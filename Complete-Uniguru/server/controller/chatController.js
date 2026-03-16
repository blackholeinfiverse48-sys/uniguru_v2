import Chat from '../models/Chat.js';
import Guru from '../models/Guru.js';
import { getRagAnswer } from '../config/rag.js';

const BRIDGE_URL = process.env.UNIGURU_BRIDGE_URL || 'http://127.0.0.1:8002/chat';
const UNIGURU_ALLOW_WEB = String(process.env.UNIGURU_ALLOW_WEB || 'false').toLowerCase() === 'true';

const extractBridgeAnswer = (payload) =>
  payload?.answer ||
  payload?.data?.response_content ||
  payload?.response ||
  '';

/**
 * @desc    Send new chat message
 * @route   POST /api/v1/chat/new
 * @access  Private
 */
export const sendChatMessage = async (req, res) => {
  try {
    const { message, chatbotId, userId, context = [], chatId } = req.body;
    console.log(`[UNIGURU NODE] Forwarding message to bridge for guru ${chatbotId}`);

    const bridgeResponse = await fetch(BRIDGE_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message,
        session_id: chatId || undefined,
        caller: 'uniguru-frontend',
        allow_web: UNIGURU_ALLOW_WEB,
        context: {
          chatbotId,
          userId,
          nodeUserId: req.user?.id,
          history: context
        }
      })
    });

    if (!bridgeResponse.ok) {
      const bridgeError = await bridgeResponse.text();
      throw new Error(`Bridge request failed with ${bridgeResponse.status}: ${bridgeError}`);
    }

    const bridgePayload = await bridgeResponse.json();
    const answer = extractBridgeAnswer(bridgePayload);

    res.status(200).json({
      success: true,
      message: 'Message sent successfully',
      aiResponse: {
        content: answer,
        metadata: {
          source: bridgePayload?.forwarded_to || BRIDGE_URL,
          confidence: bridgePayload?.verification_status === 'VERIFIED' ? 1 : bridgePayload?.verification_status === 'PARTIAL' ? 0.75 : 0.4,
          verification_status: bridgePayload?.verification_status,
          reasoning_trace: bridgePayload?.reasoning_trace,
          retrieved_chunks: bridgePayload?.data?.engine_response?.retrieved_chunks || [],
          route: bridgePayload?.data?.engine_response?.routing?.route || bridgePayload?.routing?.route || null,
          trace_id: bridgePayload?.trace_id || null
        }
      },
      bridge: bridgePayload
    });
  } catch (error) {
    console.error('Send chat message error:', error);
    res.status(500).json({
      success: false,
      message: 'Server error while sending message',
      error: error.message
    });
  }
};

/**
 * @desc    Get all user chats
 * @route   GET /api/v1/chat/all-chats
 * @access  Private
 */
export const getAllUserChats = async (req, res) => {
  try {
    const chats = await Chat.find({
      user: req.user.id,
      isActive: true,
      isArchived: false
    })
      .populate('guru', 'name subject avatar')
      .sort({ 'stats.lastActivity': -1 })
      .select('title messages stats createdAt updatedAt');

    const formattedChats = chats.map(chat => ({
      id: chat._id,
      title: chat.title,
      guru: chat.guru,
      messageCount: chat.messages.length,
      lastMessage: chat.lastMessage,
      lastActivity: chat.stats.lastActivity,
      createdAt: chat.createdAt,
      updatedAt: chat.updatedAt
    }));

    res.status(200).json({
      success: true,
      count: formattedChats.length,
      chats: formattedChats
    });
  } catch (error) {
    console.error('Get all chats error:', error);
    res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

/**
 * @desc    Get specific chat
 * @route   GET /api/v1/chat/:id
 * @access  Private
 */
export const getChat = async (req, res) => {
  try {
    const chat = await Chat.findById(req.params.id)
      .populate('guru', 'name subject avatar systemPrompt settings');

    if (!chat) {
      return res.status(404).json({
        success: false,
        message: 'Chat not found'
      });
    }

    // Check if user owns this chat
    if (chat.user.toString() !== req.user.id) {
      return res.status(403).json({
        success: false,
        message: 'Not authorized to access this chat'
      });
    }

    res.status(200).json({
      success: true,
      chat: {
        id: chat._id,
        title: chat.title,
        messages: chat.messages,
        guru: chat.guru,
        stats: chat.stats,
        settings: chat.settings,
        tags: chat.tags,
        createdAt: chat.createdAt,
        updatedAt: chat.updatedAt
      }
    });
  } catch (error) {
    console.error('Get chat error:', error);
    res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

/**
 * @desc    Update chat (title, settings, etc.)
 * @route   PUT /api/v1/chat/:id
 * @access  Private
 */
export const updateChat = async (req, res) => {
  try {
    let chat = await Chat.findById(req.params.id);

    if (!chat) {
      return res.status(404).json({
        success: false,
        message: 'Chat not found'
      });
    }

    // Check if user owns this chat
    if (chat.user.toString() !== req.user.id) {
      return res.status(403).json({
        success: false,
        message: 'Not authorized to update this chat'
      });
    }

    // Update allowed fields
    const updateFields = {};
    if (req.body.title) updateFields.title = req.body.title.trim();
    if (req.body.tags) updateFields.tags = req.body.tags;
    if (req.body.settings) updateFields.settings = { ...chat.settings, ...req.body.settings };

    chat = await Chat.findByIdAndUpdate(req.params.id, updateFields, {
      new: true,
      runValidators: true
    }).populate('guru', 'name subject avatar');

    res.status(200).json({
      success: true,
      message: 'Chat updated successfully',
      chat: {
        id: chat._id,
        title: chat.title,
        messages: chat.messages,
        guru: chat.guru,
        stats: chat.stats,
        settings: chat.settings,
        tags: chat.tags
      }
    });
  } catch (error) {
    console.error('Update chat error:', error);
    res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

/**
 * @desc    Delete all user chats
 * @route   DELETE /api/v1/chat/delete
 * @access  Private
 */
export const deleteAllUserChats = async (req, res) => {
  try {
    // Archive all user chats instead of deleting
    await Chat.updateMany(
      { user: req.user.id },
      { isArchived: true, isActive: false }
    );

    res.status(200).json({
      success: true,
      message: 'All chats deleted successfully'
    });
  } catch (error) {
    console.error('Delete all chats error:', error);
    res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

/**
 * @desc    Delete specific chat
 * @route   DELETE /api/v1/chat/:id
 * @access  Private
 */
export const deleteChat = async (req, res) => {
  try {
    const chat = await Chat.findById(req.params.id);

    if (!chat) {
      return res.status(404).json({
        success: false,
        message: 'Chat not found'
      });
    }

    // Check if user owns this chat
    if (chat.user.toString() !== req.user.id) {
      return res.status(403).json({
        success: false,
        message: 'Not authorized to delete this chat'
      });
    }

    // Archive chat instead of deleting
    chat.isArchived = true;
    chat.isActive = false;
    await chat.save();

    res.status(200).json({
      success: true,
      message: 'Chat deleted successfully'
    });
  } catch (error) {
    console.error('Delete chat error:', error);
    res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

/**
 * @desc    Clear chat messages
 * @route   DELETE /api/v1/chat/:id/messages
 * @access  Private
 */
export const clearChatMessages = async (req, res) => {
  try {
    const chat = await Chat.findById(req.params.id);

    if (!chat) {
      return res.status(404).json({
        success: false,
        message: 'Chat not found'
      });
    }

    // Check if user owns this chat
    if (chat.user.toString() !== req.user.id) {
      return res.status(403).json({
        success: false,
        message: 'Not authorized to clear this chat'
      });
    }

    // Clear messages
    await chat.clearMessages();

    res.status(200).json({
      success: true,
      message: 'Chat messages cleared successfully',
      chat: {
        id: chat._id,
        title: chat.title,
        messages: chat.messages,
        stats: chat.stats
      }
    });
  } catch (error) {
    console.error('Clear chat messages error:', error);
    res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

/**
 * @desc    Create new chat session
 * @route   POST /api/v1/chat/create
 * @access  Private
 */
export const createNewChat = async (req, res) => {
  try {
    const { guruId, title } = req.body;

    // Find the guru
    const guru = await Guru.findById(guruId);
    if (!guru) {
      return res.status(404).json({
        success: false,
        message: 'Guru not found'
      });
    }

    // Check if user owns this guru or if it's public
    if (guru.user.toString() !== req.user.id && !guru.isPublic) {
      return res.status(403).json({
        success: false,
        message: 'Not authorized to create chat with this guru'
      });
    }

    // Create new chat
    const chat = await Chat.create({
      user: req.user.id,
      guru: guruId,
      title: title || `Chat with ${guru.name}`,
      isActive: true
    });

    // Populate guru information
    await chat.populate('guru', 'name subject description');

    res.status(201).json({
      success: true,
      message: 'New chat created successfully',
      chat: {
        id: chat._id,
        title: chat.title,
        guru: chat.guru,
        createdAt: chat.createdAt,
        messageCount: chat.messageCount,
        lastActivity: chat.stats.lastActivity
      }
    });
  } catch (error) {
    console.error('Create new chat error:', error);
    res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

/**
 * @desc    Get all chats for a user
 * @route   GET /api/v1/chat/list
 * @access  Private
 */
export const getUserChats = async (req, res) => {
  try {
    const { guruId, archived = false } = req.query;

    // Build query
    const query = {
      user: req.user.id,
      isArchived: archived === 'true'
    };

    if (guruId) {
      query.guru = guruId;
    }

    // Get chats with guru information
    const chats = await Chat.find(query)
      .populate('guru', 'name subject description')
      .sort({ 'stats.lastActivity': -1 })
      .select('title guru createdAt stats.messageCount stats.lastActivity isActive');

    res.status(200).json({
      success: true,
      count: chats.length,
      chats: chats.map(chat => ({
        id: chat._id,
        title: chat.title,
        guru: chat.guru,
        createdAt: chat.createdAt,
        messageCount: chat.stats.messageCount,
        lastActivity: chat.stats.lastActivity,
        isActive: chat.isActive
      }))
    });
  } catch (error) {
    console.error('Get user chats error:', error);
    res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

/**
 * @desc    Get all chats with full data for auto-loading
 * @route   GET /api/v1/chat/all-with-data
 * @access  Private
 */
export const getAllChatsWithData = async (req, res) => {
  try {
    const { includeMessages = false } = req.query;

    // Get all active chats for the user
    const chats = await Chat.find({
      user: req.user.id,
      isActive: true,
      isArchived: false
    })
      .populate('guru', 'name subject description avatar')
      .sort({ 'stats.lastActivity': -1 });

    const formattedChats = chats.map(chat => ({
      id: chat._id,
      title: chat.title,
      guru: {
        _id: chat.guru._id,
        name: chat.guru.name,
        subject: chat.guru.subject,
        description: chat.guru.description,
        avatar: chat.guru.avatar
      },
      messageCount: chat.stats.messageCount,
      lastActivity: chat.stats.lastActivity,
      createdAt: chat.createdAt,
      isActive: chat.isActive,
      // Include messages only if requested to avoid large payloads
      messages: includeMessages === 'true' ? chat.messages : undefined
    }));

    res.status(200).json({
      success: true,
      count: formattedChats.length,
      chats: formattedChats
    });
  } catch (error) {
    console.error('Get all chats with data error:', error);
    res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

/**
 * @desc    Get specific chat with messages
 * @route   GET /api/v1/chat/:chatId
 * @access  Private
 */
export const getChatById = async (req, res) => {
  try {
    const { chatId } = req.params;

    const chat = await Chat.findById(chatId)
      .populate('guru', 'name subject description systemPrompt');

    if (!chat) {
      return res.status(404).json({
        success: false,
        message: 'Chat not found'
      });
    }

    // Check if user owns this chat
    if (chat.user.toString() !== req.user.id) {
      return res.status(403).json({
        success: false,
        message: 'Not authorized to access this chat'
      });
    }

    res.status(200).json({
      success: true,
      chat: {
        id: chat._id,
        title: chat.title,
        guru: chat.guru,
        messages: chat.messages,
        createdAt: chat.createdAt,
        stats: chat.stats,
        isActive: chat.isActive
      }
    });
  } catch (error) {
    console.error('Get chat by ID error:', error);
    res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

/**
 * @desc    Update chat (title, archive status, etc.)
 * @route   PUT /api/v1/chat/:chatId
 * @access  Private
 */
export const updateChatDetails = async (req, res) => {
  try {
    const { chatId } = req.params;
    const { title, isArchived, isActive } = req.body;

    console.log(`✏️ Backend: Updating chat ${chatId} with data:`, { title, isArchived, isActive });

    const chat = await Chat.findById(chatId);

    if (!chat) {
      console.log(`❌ Backend: Chat ${chatId} not found`);
      return res.status(404).json({
        success: false,
        message: 'Chat not found'
      });
    }

    // Check if user owns this chat
    if (chat.user.toString() !== req.user.id) {
      console.log(`🚫 Backend: User ${req.user.id} not authorized to update chat ${chatId} (owner: ${chat.user})`);
      return res.status(403).json({
        success: false,
        message: 'Not authorized to update this chat'
      });
    }

    const oldTitle = chat.title;

    // Update fields with enhanced metadata tracking
    if (title !== undefined && title.trim() !== oldTitle) {
      chat.title = title.trim();
      chat.stats.lastRename = new Date();
      chat.stats.renameCount = (chat.stats.renameCount || 0) + 1;
      console.log(`✏️ Backend: Renamed chat from "${oldTitle}" to "${title.trim()}"`);
    }
    if (isArchived !== undefined) chat.isArchived = isArchived;
    if (isActive !== undefined) chat.isActive = isActive;

    // Update last activity
    chat.stats.lastActivity = new Date();

    await chat.save();
    console.log(`✅ Backend: Chat ${chatId} updated successfully`);

    res.status(200).json({
      success: true,
      message: 'Chat updated successfully',
      chat: {
        id: chat._id,
        title: chat.title,
        isArchived: chat.isArchived,
        isActive: chat.isActive,
        stats: chat.stats
      }
    });
  } catch (error) {
    console.error('❌ Backend: Update chat error:', error);
    res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

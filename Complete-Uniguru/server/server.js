// Load environment variables FIRST
import dotenv from 'dotenv';
dotenv.config();

import express from 'express';
import cors from 'cors';
import mongoose from 'mongoose';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import cookieParser from 'cookie-parser';
import morgan from 'morgan';
import 'express-async-errors';

// Import routes
import userRoutes from './routes/userRoutes.js';
import guruRoutes from './routes/guruRoutes.js';
import chatRoutes from './routes/chatRoutes.js';
import authRoutes from './routes/authRoutes.js';
import featureRoutes from './routes/featureRoutes.js';
import ragRoutes from './routes/ragRoutes.js';

// Import middleware
import { errorHandler } from './middleware/errorHandler.js';
import { notFound } from './middleware/notFound.js';

const app = express();
const PORT = process.env.PORT || 8001;

// Security middleware
app.use(helmet({
  crossOriginResourcePolicy: { policy: "cross-origin" },
  contentSecurityPolicy: false
}));

// Rate limiting - more lenient for development
const limiter = rateLimit({
  windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS) || 15 * 60 * 1000, // 15 minutes
  max: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS) || 1000, // Increased limit for development
  message: {
    success: false,
    message: 'Too many requests from this IP, please try again later.'
  },
  standardHeaders: true,
  legacyHeaders: false,
  // Skip rate limiting for health checks and in development
  skip: (req) => {
    return req.path === '/health' || process.env.NODE_ENV === 'development';
  }
});

// Apply rate limiting conditionally
if (process.env.NODE_ENV === 'production') {
  app.use(limiter);
} else {
  // More lenient rate limiting for development
  app.use(rateLimit({
    windowMs: 1 * 60 * 1000, // 1 minute
    max: 1000, // Very high limit for development
    message: {
      success: false,
      message: 'Rate limit exceeded'
    },
    skip: (req) => req.path === '/health'
  }));
}

// CORS configuration
app.use(cors({
  origin: [
    process.env.FRONTEND_URL || 'http://localhost:5173',
    'http://localhost:5174',
    'http://localhost:3000',
    'https://www.uni-guru.in',
    'https://uni-guru.vercel.app',
    'https://3a6e99340528.ngrok-free.app',
    // Firebase hosting domains
    'https://uniguru-bf024.web.app',
    'https://uniguru-bf024.firebaseapp.com',
    // Additional Firebase domains (without trailing slash)
    'https://uniguru-bf024.web.app/',
    'https://uniguru-bf024.firebaseapp.com/'
  ],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'Cookie', 'X-Requested-With'],
  optionsSuccessStatus: 200 // For legacy browser support
}));

// Body parsing middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));
app.use(cookieParser());

// Static file serving
app.use('/uploads', express.static('uploads'));

// Logging middleware
if (process.env.NODE_ENV === 'development') {
  app.use(morgan('dev'));
} else {
  app.use(morgan('combined'));
}

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'OK',
    message: 'UniGuru Server is running',
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV
  });
});


// RAG endpoint
app.use('/rag', ragRoutes);

// API routes
app.use('/api/v1/user', userRoutes);
app.use('/api/v1/guru', guruRoutes);
app.use('/api/v1/chat', chatRoutes);
app.use('/api/v1/auth', authRoutes);
app.use('/api/v1/feature', featureRoutes);

// API routes without version (for frontend compatibility)
app.use('/api/user', userRoutes);
app.use('/api/guru', guruRoutes);
app.use('/api/chat', chatRoutes);
app.use('/api/auth', authRoutes);
app.use('/api/feature', featureRoutes);

// Legacy route support (for frontend compatibility)
app.use('/user', userRoutes);
app.use('/guru', guruRoutes);
app.use('/chat', chatRoutes);
app.use('/auth', authRoutes);
app.use('/feature', featureRoutes);

// Error handling middleware
app.use(notFound);
app.use(errorHandler);

// Database connection
const connectDB = async () => {
  try {
    const conn = await mongoose.connect(process.env.MONGODB_URI);
    console.log(`MongoDB Connected: ${conn.connection.host}`);
  } catch (error) {
    console.error('Database connection error:', error);
    process.exit(1);
  }
};

// Start server
const startServer = async () => {
  try {
    // await connectDB();
    console.log("⚠️  MongoDB connection bypassed for integration testing.");
    app.listen(PORT, () => {
      console.log(`🚀 UniGuru Server running on port ${PORT}`);
      console.log(`🌍 Environment: ${process.env.NODE_ENV}`);
      console.log(`📊 Health check: http://localhost:${PORT}/health`);
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
};

// Handle unhandled promise rejections
process.on('unhandledRejection', (err, promise) => {
  console.log('Unhandled Promise Rejection:', err.message);
  process.exit(1);
});

// Handle uncaught exceptions
process.on('uncaughtException', (err) => {
  console.log('Uncaught Exception:', err.message);
  process.exit(1);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received. Shutting down gracefully...');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('SIGINT received. Shutting down gracefully...');
  process.exit(0);
});

startServer();

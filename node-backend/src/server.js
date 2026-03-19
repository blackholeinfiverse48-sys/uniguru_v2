import cors from "cors";
import dotenv from "dotenv";
import express from "express";

import { buildUniGuruAskRequest, callUniGuruAsk, UNIGURU_ASK_URL } from "./uniguruClient.js";

dotenv.config();

const app = express();
const PORT = Number(process.env.NODE_BACKEND_PORT || 8080);

app.use(cors());
app.use(express.json({ limit: "1mb" }));

function parseContext(rawContext) {
  if (!rawContext || typeof rawContext !== "object" || Array.isArray(rawContext)) {
    return {};
  }
  return { ...rawContext };
}

app.get("/health", (_req, res) => {
  res.status(200).json({
    status: "ok",
    service: "node-backend",
    uniguru_target: UNIGURU_ASK_URL
  });
});

app.post("/api/v1/chat/query", async (req, res) => {
  try {
    const query = req.body?.query ?? req.body?.message;
    const sessionId = req.body?.session_id ?? req.body?.sessionId ?? null;
    const allowWeb = Boolean(req.body?.allow_web ?? req.body?.allowWeb ?? false);
    const context = parseContext(req.body?.context);

    const payload = buildUniGuruAskRequest({
      query,
      caller: "bhiv-assistant",
      sessionId,
      allowWeb,
      context
    });

    const engineResponse = await callUniGuruAsk(payload);
    res.status(200).json({
      success: true,
      source: "uniguru-api",
      data: engineResponse
    });
  } catch (error) {
    res.status(502).json({
      success: false,
      message: "Failed to process product chat query.",
      error: error.message
    });
  }
});

app.post("/api/v1/gurukul/query", async (req, res) => {
  try {
    const query = req.body?.query ?? req.body?.student_query;
    const studentId = req.body?.student_id ? String(req.body.student_id) : "";
    const sessionId = req.body?.session_id ?? req.body?.sessionId ?? null;
    const allowWeb = Boolean(req.body?.allow_web ?? req.body?.allowWeb ?? false);
    const context = parseContext(req.body?.context);

    const payload = buildUniGuruAskRequest({
      query,
      caller: "gurukul-platform",
      sessionId,
      allowWeb,
      context: {
        ...context,
        student_id: studentId || undefined
      }
    });

    const engineResponse = await callUniGuruAsk(payload);
    res.status(200).json({
      success: true,
      integration: "gurukul",
      student_id: studentId || null,
      source: "uniguru-api",
      data: engineResponse
    });
  } catch (error) {
    res.status(502).json({
      success: false,
      message: "Failed to process Gurukul query.",
      error: error.message
    });
  }
});

app.listen(PORT, () => {
  console.log(`Node backend listening on ${PORT}`);
});

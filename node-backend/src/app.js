import cors from "cors";
import express from "express";

import queryRoutes from "./routes/queryRoutes.js";

const app = express();

app.use(cors());
app.use(express.json({ limit: "1mb" }));
app.use(queryRoutes);

export default app;

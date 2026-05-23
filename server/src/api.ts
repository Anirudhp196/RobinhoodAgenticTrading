import express, { Request, Response } from "express";
import cors from "cors";

const PORT = 3000;
const SCORING_URL = "http://localhost:8000";

const app = express();
app.use(cors());
app.use(express.json());

app.get("/api/health", (_req: Request, res: Response) => {
  res.json({ status: "ok", service: "server" });
});

app.get("/api/scoring-health", async (_req: Request, res: Response) => {
  try {
    const upstream = await fetch(`${SCORING_URL}/health`);
    const body = await upstream.json();
    res.json({ server: "ok", scoring: body });
  } catch (err) {
    res.status(502).json({
      server: "ok",
      scoring: "unreachable",
      error: err instanceof Error ? err.message : String(err),
    });
  }
});

app.listen(PORT, () => {
  console.log(`[server] listening on http://localhost:${PORT}`);
});

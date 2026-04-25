// Next.js API Route: /api/models - 获取模型列表
import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/models`, { cache: "no-store" });
    if (res.ok) return NextResponse.json(await res.json());
  } catch { /* 后端不可用 */ }
  // 读本地 model_metadata.json
  try {
    const p = path.join(__dirname, "..", "..", "..", "..", "src", "models", "model_metadata.json");
    if (fs.existsSync(p)) return NextResponse.json(JSON.parse(fs.readFileSync(p, "utf-8")));
  } catch { /* silent */ }
  return NextResponse.json({ error: "No model data" }, { status: 503 });
}

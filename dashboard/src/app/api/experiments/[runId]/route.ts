import { NextResponse } from "next/server";
import { getExperiment } from "@/lib/data-loader";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ runId: string }> }
) {
  const { runId } = await params;
  const experiment = getExperiment(runId);
  if (!experiment) {
    return NextResponse.json({ error: "Experiment not found" }, { status: 404 });
  }
  return NextResponse.json(experiment);
}

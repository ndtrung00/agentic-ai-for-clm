import { NextResponse } from "next/server";
import { getSamples } from "@/lib/data-loader";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ runId: string }> }
) {
  const { runId } = await params;
  const samples = getSamples(runId);
  return NextResponse.json(samples);
}

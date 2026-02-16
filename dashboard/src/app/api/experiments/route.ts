import { NextResponse } from "next/server";
import { listExperiments } from "@/lib/data-loader";

export async function GET() {
  const experiments = listExperiments();
  return NextResponse.json(experiments);
}

import { TOOLS } from "@/lib/tools";
import { ToolPage } from "./ToolPage";
import { notFound } from "next/navigation";

interface Props {
  params: Promise<{ toolId: string }>;
}

export async function generateStaticParams() {
  return TOOLS.map((t) => ({ toolId: t.id }));
}

export default async function Page({ params }: Props) {
  const { toolId } = await params;
  const tool = TOOLS.find((t) => t.id === toolId);
  if (!tool) notFound();
  return <ToolPage tool={tool} />;
}

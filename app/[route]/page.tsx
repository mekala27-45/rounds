import { notFound } from "next/navigation";
import { RoundsApp } from "@/components/rounds-app";
const routes = ["ed","inpatient","beds","icu","primary-care","pharmacy","lab","imaging","surgery","finance","informatics","cohorts","measures","models","monitoring","quality","explore","report","audit","patients"];
export default async function Department({params}:{params:Promise<{route:string}>}) {
  const {route} = await params;
  if (!routes.includes(route)) notFound();
  return <RoundsApp route={route} />;
}

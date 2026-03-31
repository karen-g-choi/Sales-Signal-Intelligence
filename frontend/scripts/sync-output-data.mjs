import fs from "node:fs";
import path from "node:path";

const projectRoot = path.resolve(process.cwd(), "..");
const sourceDir = path.join(projectRoot, "output");
const targetDir = path.join(process.cwd(), "public", "data");

const files = [
  "fact_orders.csv",
  "fact_invoices.csv",
  "fact_events.csv",
  "fact_promotions.csv",
  "dim_customer.csv",
  "dim_product.csv",
  "target_monthly.csv",
];

fs.mkdirSync(targetDir, { recursive: true });

for (const file of files) {
  fs.copyFileSync(path.join(sourceDir, file), path.join(targetDir, file));
}

console.log(`Synced ${files.length} CSV files into public/data`);

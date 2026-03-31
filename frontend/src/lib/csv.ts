import Papa from "papaparse";

export async function loadCsv<T>(fileName: string): Promise<T[]> {
  const cacheBuster = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const response = await fetch(`/data/${fileName}?v=${cacheBuster}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to load ${fileName}`);
  }

  const text = await response.text();
  const parsed = Papa.parse<T>(text, {
    header: true,
    skipEmptyLines: true,
    dynamicTyping: true,
  });

  if (parsed.errors.length > 0) {
    throw new Error(parsed.errors[0].message);
  }

  return parsed.data;
}

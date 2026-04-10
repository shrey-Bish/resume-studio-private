import { chromium } from "playwright";

const [, , inputPath, outputPath] = process.argv;

if (!inputPath || !outputPath) {
  console.error("Usage: node render_pdf.mjs <input-html> <output-pdf>");
  process.exit(1);
}

const browser = await chromium.launch();

try {
  const page = await browser.newPage();
  await page.goto(`file://${inputPath}`, { waitUntil: "load" });
  await page.pdf({
    path: outputPath,
    format: "A4",
    printBackground: true,
    margin: {
      top: "0.2in",
      right: "0.2in",
      bottom: "0.2in",
      left: "0.2in",
    },
  });
} finally {
  await browser.close();
}


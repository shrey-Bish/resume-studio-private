import { chromium } from "playwright";

const [, , url] = process.argv;

if (!url) {
  console.error("Usage: node fetch_job.mjs <url>");
  process.exit(1);
}

const browser = await chromium.launch();

try {
  const page = await browser.newPage({
    userAgent:
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
  });
  await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });

  const payload = await page.evaluate(() => {
    const pickText = () => {
      const candidates = [
        document.querySelector("main"),
        document.querySelector("article"),
        document.querySelector("[role='main']"),
        document.body,
      ].filter(Boolean);

      let best = "";
      for (const node of candidates) {
        const text = node.innerText?.trim() || "";
        if (text.length > best.length) best = text;
      }
      return best;
    };

    const title =
      document.querySelector("h1")?.textContent?.trim() ||
      document.title ||
      "Job Description";

    return {
      title,
      text: pickText(),
    };
  });

  console.log(JSON.stringify(payload));
} finally {
  await browser.close();
}


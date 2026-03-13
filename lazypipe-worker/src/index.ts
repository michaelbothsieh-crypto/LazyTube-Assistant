import puppeteer from '@cloudflare/puppeteer';

export interface Env {
	MYBROWSER: Fetcher;
}

export default {
	async fetch(request: Request, env: Env): Promise<Response> {
		const { searchParams } = new URL(request.url);
		let url = searchParams.get('url');

		// 處理 POST 請求 (也可以把 url 放在 body)
		if (request.method === 'POST') {
			try {
				const body = await request.json();
				if (body.url) url = body.url;
			} catch (e) {
				// ignore
			}
		}

		if (!url) {
			return new Response('請提供 url 參數', { status: 400 });
		}

		let browser;
		try {
			// 啟動 Cloudflare 託管的瀏覽器
			browser = await puppeteer.launch(env.MYBROWSER);
			const page = await browser.newPage();
			
			// 模擬真實瀏覽器的 User-Agent，降低被擋的機率
			await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
			
			// 前往目標網址，等待網路閒置 (確保 JavaScript 渲染完成)
			await page.goto(url, { waitUntil: 'networkidle2' });
			
			// 抓取網頁標題與純文字內容
			const data = await page.evaluate(() => {
				// 移除腳本和樣式標籤以清理文字
				const scripts = document.querySelectorAll('script, style');
				scripts.forEach(s => s.remove());
				
				return {
					title: document.title,
					content: document.body.innerText.trim()
				};
			});
			
			await browser.close();

			// 回傳 JSON
			return Response.json({
				success: true,
				url: url,
				title: data.title,
				content: data.content
			});
		} catch (error: any) {
			if (browser) await browser.close();
			return Response.json({ 
				success: false, 
				error: error.message 
			}, { status: 500 });
		}
	},
};

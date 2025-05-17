from flask import Flask, request, jsonify
import aiohttp
import asyncio
import logging
from urllib.parse import parse_qs, urlparse

app = Flask(__name__)

cookies = {
    'PANWEB': '1',
    'browserid': 'p4nVrnlkUVKcnbbJHnIClAhSL5uXs01e-0svx0bm7KHLUB6wIVvCUNGLIpU=',
    'lang': 'en',
    '__bid_n': '1900b9f02442253dfe4207',
    'ndut_fmt': '5E7E5AFA065E159EF56CFE164FCF084C72B603BE3611911C28550443BDC08A4B',
    '__stripe_mid': 'b85d61d2-4812-4eeb-8e41-b1efb3fa2a002a54d5',
    'ndus': 'YylKpiCteHuiYEqq8n75Tb-JhCqmg0g4YMH03MYD',
    'csrfToken': 'zAVdnQAVegC92-ah6pmLf6Dl',
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Accept': '*/*',
    'Connection': 'keep-alive',
}

def find_between(string, start, end):
    start_index = string.find(start) + len(start)
    end_index = string.find(end, start_index)
    return string[start_index:end_index]

def extract_thumbnail_dimensions(url: str) -> str:
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    size_param = params.get('size', [''])[0]
    if size_param:
        parts = size_param.replace('c', '').split('_u')
        if len(parts) == 2:
            return f"{parts[0]}x{parts[1]}"
    return "original"

async def get_formatted_size_async(size_bytes):
    try:
        size_bytes = int(size_bytes)
        size = size_bytes / (1024 * 1024) if size_bytes >= 1024 * 1024 else (
            size_bytes / 1024 if size_bytes >= 1024 else size_bytes
        )
        unit = "MB" if size_bytes >= 1024 * 1024 else ("KB" if size_bytes >= 1024 else "bytes")
        return f"{size:.2f} {unit}"
    except Exception as e:
        print(f"Error getting formatted size: {e}")
        return None

async def fetch_download_link_async(url):
    try:
        async with aiohttp.ClientSession(cookies=cookies, headers=headers) as session:
            async with session.get(url) as response1:
                response1.raise_for_status()
                response_data = await response1.text()
                js_token = find_between(response_data, 'fn%28%22', '%22%29')
                log_id = find_between(response_data, 'dp-logid=', '&')

                if not js_token or not log_id:
                    return None

                request_url = str(response1.url)
                surl = request_url.split('surl=')[1]
                params = {
                    'app_id': '250528',
                    'web': '1',
                    'channel': 'dubox',
                    'clienttype': '0',
                    'jsToken': js_token,
                    'dplogid': log_id,
                    'page': '1',
                    'num': '20',
                    'order': 'time',
                    'desc': '1',
                    'site_referer': request_url,
                    'shorturl': surl,
                    'root': '1'
                }

                async with session.get('https://www.1024tera.com/share/list', params=params) as response2:
                    response_data2 = await response2.json()

                    if 'list' not in response_data2:
                        return None

                    if response_data2['list'][0]['isdir'] == "1":
                        params.update({
                            'dir': response_data2['list'][0]['path'],
                            'order': 'asc',
                            'by': 'name',
                            'dplogid': log_id
                        })
                        params.pop('desc')
                        params.pop('root')

                        async with session.get('https://www.1024tera.com/share/list', params=params) as response3:
                            response_data3 = await response3.json()
                            if 'list' not in response_data3:
                                return None
                            return response_data3['list']

                    return response_data2['list']
    except aiohttp.ClientResponseError as e:
        print(f"Error fetching download link: {e}")
        return None

async def format_message(link_data):
    thumbnails = {}
    if 'thumbs' in link_data:
        for key, url in link_data['thumbs'].items():
            if url:
                dimensions = extract_thumbnail_dimensions(url)
                thumbnails[dimensions] = url

    return {
        'Title': link_data["server_filename"],
        'Size': await get_formatted_size_async(link_data["size"]),
        'Direct Download Link': link_data["dlink"],
        'Thumbnails': thumbnails
    }

@app.route('/')
def hello_world():
    return {'status': 'success', 'message': 'Working Fully', 'Contact': '@ftmdeveloperz'}

@app.route('/api', methods=['GET'])
async def Api():
    try:
        url = request.args.get('url', 'No URL Provided')
        logging.info(f"Received request for URL: {url}")
        link_data = await fetch_download_link_async(url)
        if link_data:
            tasks = [format_message(item) for item in link_data]
            formatted_message = await asyncio.gather(*tasks)
        else:
            formatted_message = None
        return jsonify({'ShortLink': url, 'Extracted Info': formatted_message, 'status': 'success'})
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return jsonify({'status': 'error', 'message': str(e), 'Link': url})

@app.route('/help', methods=['GET'])
async def help():
    try:
        return jsonify({
            'Info': "There is Only one Way to Use This as Show Below",
            'Example': 'https://terabox-dl.vercel.app/api?url=https://terafileshare.com/s/1_1SzMvaPkqZ-yWokFCrKyA',
            'Example2': 'https://terabox-dl.vercel.app/api2?url=https://terafileshare.com/s/1_1SzMvaPkqZ-yWokFCrKyA'
        })
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return jsonify({
            'Info': "There is Only one Way to Use This as Show Below",
            'Example': 'https://terabox-dl.vercel.app/api?url=https://terafileshare.com/s/1_1SzMvaPkqZ-yWokFCrKyA',
            'Example2': 'https://terabox-dl.vercel.app/api2?url=https://terafileshare.com/s/1_1SzMvaPkqZ-yWokFCrKyA'
        })

# Run the app if this is the main module
if __name__ == '__main__':
    import uvicorn
    uvicorn.run("terabox_api:app", host="0.0.0.0", port=8000, reload=True)

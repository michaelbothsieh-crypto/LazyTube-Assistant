import json
from pathlib import Path


def test_requested_podcast_sources_are_registered_for_website_scanner():
    kols = json.loads(Path("data/website_kols.json").read_text(encoding="utf-8"))
    by_id = {kol["kol_id"]: kol for kol in kols}

    expected = {
        "manny_newsletter": "https://feed.firstory.me/rss/user/ckb7oop2y0yit0873vc36njil",
        "miula_viewpoint": "https://feeds.soundon.fm/podcasts/b8f5a471-f4f7-4763-9678-65887beda63a.xml",
        "jenny_us_stock": "https://feeds.soundon.fm/podcasts/4a8660a0-e0d0-490b-8d46-c28219606f47.xml",
        "jiuclass": "https://feeds.soundon.fm/podcasts/70907bd6-d0ae-4b64-bc38-2bf48ae4fc36.xml",
        "caalaw": "https://feed.firstory.me/rss/user/clcftm46z000201z45w1c47fi",
        "macromicro": "https://feeds.soundon.fm/podcasts/d2aab16c-3a70-4023-b52b-e50f07852ecd.xml",
    }

    for kol_id, rss_url in expected.items():
        assert by_id[kol_id]["rss_url"] == rss_url

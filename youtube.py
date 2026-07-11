from datetime import datetime, timezone
import xml.etree.ElementTree as ET

import requests


FEED_URL = "https://www.youtube.com/feeds/videos.xml"
NS = {
	"atom": "http://www.w3.org/2005/Atom",
	"yt": "http://www.youtube.com/xml/schemas/2015",
}

def _parse_time(value):
	return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
		timezone.utc)

def _format_time(value):
	return value.strftime("%Y-%m-%dT%H:%M:%SZ")

def get_channel_videos(channel_id, published_after=None, max_results=50):
	if max_results <= 0:
		return []
	
	published_after = _parse_time(published_after) if published_after else None
	resp = requests.get(
		FEED_URL, params={"channel_id": channel_id}, timeout=10)
	resp.raise_for_status()
	
	videos = []
	root = ET.fromstring(resp.content)
	for entry in root.findall("atom:entry", NS):
		published_at = _parse_time(entry.findtext("atom:published", "", NS))
		if published_after and published_at <= published_after:
			continue
		
		video_id = entry.findtext("yt:videoId", "", NS)
		videos.append({
			"id": video_id,
			"title": entry.findtext("atom:title", "", NS),
			"url": f"https://youtu.be/{video_id}",
			"published_at": _format_time(published_at),
		})
		if len(videos) >= max_results:
			break
	
	return videos

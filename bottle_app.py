# -*- coding: utf-8 -*-

from bottle import default_app, route, request, response, post, static_file
import pathy, ctl, json, traceback

@route('/upd_c3z82k4f')
def handle_cron():
	try:
		ctl.entry("j394c02mx04nc23r4/keepalive")
		
		pathy_bot = pathy.PathyRobot()
		pathy_bot.pathy_upd()
		return "Updated!"
	except Exception:
		print("Failed to update: " + traceback.format_exc())
		return "Failed to update :("

@route('/upd_m4cc7ld8')
def handle_cron_monday():
	try:
		pathy_bot = pathy.PathyRobot()
		pathy_bot.on_monday_cron()
		return "Updated!"
	except Exception:
		print("Failed to handle monday cron: " + traceback.format_exc())
		return "Failed to handle monday cron :("

@route('/upd_Yc8d5ld3')
def handle_yt_check():
	try:
		pathy_bot = pathy.PathyRobot()
		pathy_bot.on_yt_check()
		return "Updated!"
	except Exception:
		print("Failed to check for new yt videos: " + traceback.format_exc())
		return "Failed to check for new yt videos :("

@post('/upd_x6j2jxv8')
def handle_tg_update():
	try:
		update_json = request.body.read().decode("utf-8")
		update = json.loads(update_json)
		pathy_bot = pathy.PathyRobot()
		pathy_bot.on_tg_update(update)
		return "Updated!"
	except Exception:
		print("Failed to handle tg update: " + traceback.format_exc())
		return "Failed to handle tg update :("

@route('/crafting_preview')
def handle_crafting_prefiew():
	try:
		pathy_bot = pathy.PathyRobot()
		file_path = pathy_bot.get_crafting_preview(request.query.get("icons"))

		if file_path:
			return static_file(str(file_path), root="/")
		else:
			return
	except Exception:
		print("Failed to generate crafting preview: " + traceback.format_exc())
		return "Failed to generate crafting preview :("


@route("/pathy/<action:re:.+>", method=["POST", "GET"])
def on_pathy_request(action):
	params = request.query.__dict__.get("dict") or {}
	resp = ctl.entry(
		action, params, request.body.read())
	
	if type(resp) == tuple:
		if resp[0] == "file":
			return static_file(str(resp[1]), root="/")
	
	return str(resp)

application = default_app()

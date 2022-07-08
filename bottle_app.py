# -*- coding: utf-8 -*-

from bottle import default_app, route, request, static_file
import ctl

@route("/pathy/<action:re:.+>", method=["POST", "GET"])
def on_pathy_request(action):
	params = request.query.__dict__.get("dict") or {}
	resp = ctl.entry(
		action, params, request.body.read(), from_web=True)
	
	if type(resp) == tuple:
		if resp[0] == "file":
			return static_file(str(resp[1]), root="/")
	
	return str(resp)

application = default_app()

from datetime import datetime
from flask import Flask
from flask import render_template
from flask import request
from flask import send_file
import io
import time 
import db_init 

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib as mpl
import matplotlib.ticker as ticker
app = Flask(__name__)

prop = fm.FontProperties(fname = "/home/clear/.fonts/Roboto-Light.ttf")

def getPlayers(hours):
	counts = []
	times = []
	gms = []
	curTime = time.time()
	
	numScans = hours * 4 + 1
	
	cursor = db_init.db["scans"].find({"time": {"$gt": curTime - 900 * numScans - 900 * hours}}).sort([("time", -1)]).limit(numScans)
	lastTime = cursor[0]["time"]
	firstTime = cursor[cursor.count(True) - 1]["time"]
	
	for result in cursor:
		times.append(int(result["time"]))
		counts.append(result["allplayers"])
		gms.append(result["gms"])

	times.reverse()	
	counts.reverse()
	gms.reverse()
	return (counts, times, gms)

def initGraphSystem():
	plt.grid(b = True, which = "major", axis = "both")
	plt.ylim([0, 100])
	plt.tick_params(axis = "both", which = "both", top = False, right = False)
	plt.yticks(fontproperties = prop)
	plt.xticks(fontproperties = prop)
	plt.tight_layout(1.5)


def makeGraph(size, hours, title):
	numHours = int(hours)
	sizes = {
		"big": (8, 4, 100),
		"small": (6, 3, 75)
	}
	counts, times, gms = getPlayers(numHours)
	length = len(counts)


	timeLabels = [datetime.fromtimestamp(x).strftime('%H:%M\n%Y-%m-%d') for x in times]
	fig = plt.figure(figsize = (sizes[size][0], sizes[size][1]))
	initGraphSystem()
	plt.plot(times, counts, color = "#B43C3C", linestyle = "-")
	plt.plot(times, gms, color = "#3C50B4", linestyle = "-")
	plt.fill_between(times, counts, color = "#CC4444")
	plt.fill_between(times, gms, color = "#445BCC")
	fig.suptitle(title, fontproperties = prop)
	plt.xticks([times[0], times[length//4], times[length//2], times[length//4*3], times[-1]], [timeLabels[0], timeLabels[length//4], timeLabels[length//2], timeLabels[length//4*3], "     Now          a"], fontproperties = prop)
	plt.xlim([times[0], times[-1]])
	legend = plt.legend(("Total players", "GMs"), prop = prop)
	legend.get_frame().set_alpha(0.25)
	img = io.BytesIO()
	fig.savefig(img, dpi = sizes[size][2])
	plt.close(fig)
	img.seek(0)

	return img

def makeWeekdayGraph(size):
	sizes = {
		"big": (8, 4, 100),
		"small": (6, 3, 75)
	}

	cursor = db_init.db["scans"].find()
	days = [0] * 7
	dayCount = [0] * 7
	for r in cursor:
		dt = datetime.fromtimestamp(r["time"])
		days[dt.weekday()] += r["allplayers"]
		dayCount[dt.weekday()] += 1
	
	for i, v in enumerate(days):
		days[i] = v // dayCount[i];

	days = days[-1:] + days[:-1]
	daysOfWeek = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
	fig = plt.figure(figsize = (sizes[size][0], sizes[size][1]))
	initGraphSystem()
	plt.plot(days, color = "#B43C3C", linestyle = "-")
	plt.fill_between(list(range(7)), days, color = "#CC4444")
	fig.suptitle("Average players by weekday", fontproperties = prop)
	plt.xticks(list(range(7)), daysOfWeek, fontproperties = prop)
	plt.xlim([0, 6])
	img = io.BytesIO()
	fig.savefig(img, dpi = sizes[size][2])
	plt.close(fig)
	img.seek(0)

	return img

@app.route("/weekdays")
def weekdays():
	return send_file(makeWeekdayGraph("big"), mimetype = "image/png")


@app.route("/graph/<size>/<timeFrame>/<num>")
def getGraph(size, timeFrame, num):
	if size not in ["big", "small"]:
		size = "small"
	if timeFrame not in ["hours", "days", "weeks", "months"]:
		timeFrame = "hours"

	multiples = {"hours": 1, "days": 24, "weeks": 168, "months": 720}
	try:
		numHours = int(num) * multiples[timeFrame]
	except:
		numHours = 3

	title = "Player count (last {} {})".format(num, timeFrame)
	img = makeGraph(size, numHours, title)
	return send_file(img, mimetype = "image/png")


@app.route("/")
def stats():
	result = db_init.db["scans"].aggregate([{"$group": {"_id": "$y", "mean": {"$avg": "$allplayers"}}}])
	avgPlayerCount = result["result"][0]["mean"]
	result = db_init.db["scans"].find().sort([("allplayers", -1)]).limit(1)[0]
	maxPlayerCount = result["allplayers"]
	maxPlayerTime = datetime.fromtimestamp(result["time"]).strftime("%Y-%m-%d")

	numScans = db_init.db["scans"].count()

	result = db_init.db["scans"].find().sort([("time", -1)]).limit(1)[0]
	curtime = time.time()
	lastScan = round((curtime - result["time"]) / 60)

	result = db_init.db["scans"].aggregate([{"$group": {"_id": "$y", "mean": {"$avg": "$gms"}}}])
	avgGMCount = result["result"][0]["mean"]

	result = db_init.db["scans"].find().sort([("gms", -1)]).limit(1)[0]
	maxGMCount = result["gms"]
	maxGMTime = datetime.fromtimestamp(result["time"]).strftime("%Y-%m-%d")

	result = db_init.db["scans"].find({"gms": {"$gt": 0}})
	GMAvailability = round(result.count() / numScans * 100, 1)

	statDict = {
		"avgPlayerCount": round(avgPlayerCount),
		"maxPlayerCount": [maxPlayerCount, maxPlayerTime],
		"lastScan": lastScan,
		"numScans": numScans,
		"totalSeen": db_init.db["normals"].count() + db_init.db["gms"].count(),
		"avgGMCount": round(avgGMCount),
		"maxGMCount": [maxGMCount, maxGMTime],
		"GMAvailability": GMAvailability
	}
	return render_template("stats.html", stats = statDict)

@app.route("/graphs")
def graphs():
	return render_template("graphs.html")

@app.route("/players", methods=["GET"])
def players():
	searchQ = request.args.get("search")
	if searchQ is not None:
		# search code
		result = db_init.db["normals"].find({"charid": searchQ})
		if result is None:
			result = db_init.db["gms"].find({"charid": searchQ})
		
		if result.count() == 0:
			f = False
			data = "Player {} could not be found.".format(searchQ)
		else:
			f = True
			data = result[0]
		return render_template("players.html", q = True, searchQ = searchQ, f = f, data = data)
	
	#stats code
	return render_template("players.html", searchQ = "")

if __name__ == "__main__":
	app.run(host="0.0.0.0", port=5001, debug=False)

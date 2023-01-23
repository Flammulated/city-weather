from flask import Flask, render_template, request
import requests, calendar

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/weather", methods=["POST","GET"])
def weather():
    if request.method == "POST":
        city = request.form["city"]
        country = request.form["country"]
        results = searchResults(city, country)
        if (not city.isspace()) and city and results:
            variables = weatherData(results)
            return render_template("weather.html", cityName=variables[0], timezone=variables[1],\
                currentWeather=variables[2], dailyForecast=variables[3])
        else:
            return render_template("nothing.html", cityName=city, countryName=country)
    else:
        return render_template("index.html")

def searchResults(city, country):
    # Returns False if there are no search results
    citySearch = requests.get(f"https://api.teleport.org/api/cities/?search={city},{country}")
    cityData = citySearch.json()
    citySearchResults = cityData["_embedded"]["city:search-results"]
    if not citySearchResults:
        return False
    else:
        return citySearchResults

def weatherData(results):
    cityName = f"{results[0]['matching_full_name']}"

    cityInfo = requests.get(results[0]["_links"]["city:item"]["href"])
    cityData = cityInfo.json()
    latitude = cityData["location"]["latlon"]["latitude"]
    longitude = cityData["location"]["latlon"]["longitude"]
    apiLink = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&hourly=temperature_2m,weathercode&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=auto&current_weather=True"
    weatherSearch = requests.get(apiLink)
    weatherData = weatherSearch.json()

    currentTime = weatherData["current_weather"]["time"]
    offsetHour = int(int(weatherData["utc_offset_seconds"])/3600)
    offsetOutput = ""
    if offsetHour > 0:
        offsetOutput = f" +{offsetHour} hours"
    elif offsetHour < 0:
        offsetOutput = f" {offsetHour} hours"
    timeZone = weatherData["timezone"].replace("_", " ") + f" (UTC/GMT{offsetOutput})"

    hourlyData = weatherData["hourly"]
    hourTempUnit = weatherData["hourly_units"]["temperature_2m"]
    currentTimeIndex = hourlyData["time"].index(currentTime)
    currentWeather = {"date":timeFormatter(hourlyData['time'][currentTimeIndex])[0],\
        "time":timeFormatter(hourlyData['time'][currentTimeIndex])[1],\
        "temp":f"{hourlyData['temperature_2m'][currentTimeIndex]}{hourTempUnit}",\
        "weather":weathercodeFormatter(hourlyData["weathercode"][currentTimeIndex])}
    
    dailyData = weatherData["daily"]
    dailyForecast = []
    currentDay = dailyData["time"].index(currentTime.split("T")[0])
    dailyMaxTempUnit = weatherData["daily_units"]["temperature_2m_max"]
    dailyMinTempUnit = weatherData["daily_units"]["temperature_2m_min"]
    for i in range(1,6):
        date = timeFormatter(dailyData["time"][currentDay+i])
        weatherDescription = weathercodeFormatter(dailyData["weathercode"][currentDay+i])
        maxTemp = f"{dailyData['temperature_2m_max'][currentDay+i]}{dailyMaxTempUnit}"
        minTemp = f"{dailyData['temperature_2m_min'][currentDay+i]}{dailyMinTempUnit}"
        dailyForecast.append({"date":date, "weather":weatherDescription, "max_temp":maxTemp,\
        "min_temp":minTemp})
    
    return (cityName, timeZone, currentWeather, dailyForecast)

def timeFormatter(time):
    if "T" in time:
        temporary = time.split("T")
        date = temporary[0].split("-")
        month = calendar.month_name[int(date[1])]
        hour = int(temporary[1][:2])
        if hour <= 11:
            if hour == 0:
                hourOutput = "12 AM"
            else:
                hourOutput = f"{hour} AM"
        else:
            if hour == 12:
                hourOutput = "12 PM"
            else:
                hourOutput = f"{hour-12} PM"
        return [f"{month} {date[2]}, {date[0]}", hourOutput]
    else:
        temporary = time.split("-")
        month = calendar.month_name[int(temporary[1])]
        return f"{month} {temporary[2]}, {temporary[0]}"

def weathercodeFormatter(code):
    weatherCodes = {"0":"Clear sky", "1":"Mainly clear", "2":"Partly cloudly", "3":"Overcast",\
    "45":"Fog", "48":"Depositing rime fog", "51":"Light drizzle", "53":"Moderate drizzle",\
    "55":"Dense drizzle", "56":"Light freezing drizzle", "57":"Dense freezing drizzle",\
    "61":"Slight rain", "63":"Moderate rain", "65":"Heavy rain", "66":"Light freezing rain",\
    "67":"Heavy freezing rain", "71":"Slight snow fall", "73":"Moderate snow fall",\
    "75":"Heavy snow fall", "77":"Snow grains", "80":"Slight rain showers",\
    "81":"Moderate rain showers", "82":"Violent rain showers", "85":"Slight snow showers",\
    "86":"Heavy snow showers", "95":"Slight or moderate thunderstorm",\
    "96":"Thunderstorm with slight hail", "99":"Thunderstorm with heavy hail"}
    # Thunderstorm forecast with hail is only available in Central Europe (95, 96, 99)
    if (str(code)) in weatherCodes:
        return weatherCodes[str(code)]
    else:
        return "N/A"

if __name__ == "__main__":
    app.run(debug=True, port=8000)
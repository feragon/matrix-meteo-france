import requests
from datetime import datetime, timedelta, date


class City(object):
    def __init__(self, api_data):
        self._id = api_data["indicatif"]
        self._name = api_data["nom"]
        self._postal_code = api_data["codePostal"]
        self._rain_available = api_data["couvertPluie"]
        self._country = api_data["pays"]
        self._department_name = api_data["nomDept"]
        self._department_number = api_data["numDept"]
        self._region = api_data["region"]
        self._latitude = api_data["latitude"]
        self._longitude = api_data["longitude"]

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def postal_code(self):
        return self._postal_code

    @property
    def rail_available(self):
        return self._rain_available

    @property
    def country(self):
        return self._country

    @property
    def department_name(self):
        return self._department_name

    @property
    def department_number(self):
        return self._department_number

    @property
    def region(self):
        return self._region

    @property
    def latitude(self):
        return self._latitude

    @property
    def longitude(self):
        return self._longitude


class Forecast(object):
    def __init__(self, api_data):
        self._date = date.fromtimestamp(api_data["date"] / 1000)
        self._moment = api_data["moment"]
        self._description = api_data["description"]
        self._wind_speed = api_data["vitesseVent"]
        self._gust_speed = api_data["forceRafales"]
        self._min_temperature = api_data["temperatureMin"]
        self._max_temperature = api_data["temperatureMax"]
        self._uv_index = api_data["indiceUV"]
        self._rain_probability = api_data["probaPluie"] or 0
        self._snow_probability = api_data["probaNeige"] or 0
        self._frost_probability = api_data["probaGel"] or 0

    @property
    def date(self):
        return self._date

    @property
    def moment(self):
        return self._moment

    @property
    def description(self):
        return self._description

    @property
    def wind_speed(self):
        return self._wind_speed

    @property
    def gust_speed(self):
        return self._gust_speed

    @property
    def min_temperature(self):
        return self._min_temperature

    @property
    def max_temperature(self):
        return self._max_temperature

    @property
    def uv_index(self):
        return self._uv_index

    @property
    def snow_probability(self):
        return self._snow_probability

    @property
    def rain_probability(self):
        return self._rain_probability

    @property
    def frost_probability(self):
        return self._frost_probability

    
class Forecasts(object):
    def __init__(self, city, forecasts_data, nb_days):
        self._city = city
        self._forecasts = []

        for key, forecast in forecasts_data["previsions"].items():
            if int(key.split("_")[0]) == nb_days:
                break

            self._forecasts.append(Forecast(forecast))

    @property
    def city(self):
        return self._city

    @property
    def forecasts(self):
        return self._forecasts


class RainForecastPart(object):
    def __init__(self, api_data, begin_time, end_time):
        self._text = api_data["niveauPluieText"]
        self._rain_level = api_data["niveauPluie"]
        self._color = api_data["color"]
        self._begin_time = begin_time
        self._end_time = end_time

    @property
    def text(self):
        return self._text

    @property
    def rain_level(self):
        return self._rain_level

    @property
    def color(self):
        return self._color

    @property
    def begin_time(self):
        return self._begin_time

    @property
    def end_time(self):
        return self._end_time


class RainForecast(object):
    def __init__(self, api_data):
        self._lastUpdate = api_data['lastUpdate']
        self._expiration = datetime(int(api_data['echeance'][:4]),
                                    int(api_data['echeance'][4:6]),
                                    int(api_data['echeance'][6:8]),
                                    int(api_data['echeance'][8:10]),
                                    int(api_data['echeance'][10:12]))
        self._texts = api_data["niveauPluieText"]
        self._parts = []

        i = 0
        for forecast in api_data["dataCadran"]:
            self._parts.append(RainForecastPart(forecast, self._expiration + timedelta(minutes=5 * i), self._expiration + timedelta(minutes=5 * (i + 1))))
            i = i + 1

    @property
    def last_update(self):
        return self._lastUpdate

    @property
    def expiration(self):
        return self._expiration

    @property
    def texts(self):
        return self._texts

    @property
    def parts(self):
        return self._parts


class MeteoFranceAPI(object):
    @staticmethod
    def search(city):
        r = requests.get("http://ws.meteofrance.com/ws/getLieux/" + str(city) + ".json")
        result = r.json()
        if len(result["result"]["france"]) > 0:
            return City(result["result"]["france"][0])
        else:
            raise RuntimeError("Ville non trouvée")

    @staticmethod
    def get_forecast(city_id, nb_days):
        r = requests.get("http://ws.meteofrance.com/ws/getDetail/france/" + str(city_id) + ".json")
        result = r.json()
        return Forecasts(City(result["result"]["ville"]), result["result"], nb_days)

    @staticmethod
    def get_rain_hour(id_ville):
        r = requests.get("http://www.meteofrance.com/mf3-rpc-portlet/rest/pluie/" + str(id_ville))
        return RainForecast(r.json())

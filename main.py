import os
import redis
import sqlalchemy
import uvicorn
import requests
import psycopg2
from psycopg2.extensions import connection
from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI, Request, Form, status, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from uuid import uuid4
from passlib.context import CryptContext
from typing import Union
from dotenv import load_dotenv
from pydantic.dataclasses import dataclass
from pydantic import BaseModel

load_dotenv()
r = redis.Redis(decode_responses=True, host=os.getenv('redis_host'))
app = FastAPI()
app.mount("/pics", StaticFiles(directory="./pics"), name="pics")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
templates = Jinja2Templates(directory="templates")


def connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        dbname=os.getenv('db_name'),
        user=os.getenv('db_user'),
        host=os.getenv('db_host'),
        password=os.getenv('db_password'),
        port='5432'
    )


base = automap_base()
class User(base):
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}

    username = Column(String, primary_key=True)
    hashed_password = Column(String)
    city = Column(String)


engine = sqlalchemy.create_engine('postgresql+psycopg2://', creator=connect)
base.prepare(autoload_with=engine)
Session = sessionmaker(engine)


@dataclass
class WeatherData(BaseModel):
    weather: list
    main: dict
    name: str

    @property
    def info(self) -> list:
        temp_c = round(self.main['temp'] - 273.15, 2)
        return[self.weather[0]['main'], self.main['humidity'], self.main['pressure'], temp_c, self.name]

    class Config:
        allow_population_by_field_name = True


class UserAuthorization:
    async def __call__(self, request: Request):
        token = request.cookies.get("token")
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Najpierw się zaloguj")
        if not r.get(token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Najpierw się zaloguj")
        pass


def select_user(username) -> Union[sqlalchemy.orm.query.Query, None]:
    with Session() as session:
        user = session.query(User).filter_by(username=username)
    if user.count() == 1:
        return user[0]
    return None


def get_weather(city) -> list:
    city_call = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={os.getenv("appid")}'
    req = requests.get(city_call)
    weather_data = WeatherData.parse_obj(req.json())
    return weather_data.info


@app.get("/", response_class=HTMLResponse)
async def root(request: Request, wrong_cred: bool = False, user_exists: bool = False) -> Jinja2Templates.TemplateResponse:
    x = templates.TemplateResponse("index.html", {"request": request, "wrong_cred": wrong_cred, "user_exists": user_exists})
    return x


@app.get("/weather", response_class=HTMLResponse, dependencies=[Depends(UserAuthorization())])
async def weather(request: Request, city: str = 'Poznań', not_found: bool = False) -> Jinja2Templates.TemplateResponse:
    weather_info = get_weather(city)
    dic = {"request": request, "weather_type": weather_info[0], "humidity": weather_info[1], "pressure": weather_info[2],
           'temp': weather_info[3], "city": weather_info[4], "not_found": not_found}
    x = templates.TemplateResponse("weather.html", dic)
    return x


def change_default(city, token) -> None:
    username = r.get(token)
    if username:
        with Session() as session:
            session.query(User).filter_by(username=username).update({User.city: city})
            session.commit()
    pass


@app.post("/weather", dependencies=[Depends(UserAuthorization())])
async def change_city(request: Request, city: str = Form(...), old_city: str = Form(...)) -> RedirectResponse:
    city_call = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid=adf0fda1db34d68d7073d8d88749962c'
    response = requests.get(city_call)
    try:
        response.raise_for_status()
        response = RedirectResponse(url=f'/weather/?city={city}', status_code=status.HTTP_302_FOUND)
        change_default(city, request.cookies.get("token"))
        return response
    except requests.exceptions.HTTPError:
        response = RedirectResponse(url=f'/weather/?city={old_city}&not_found=true', status_code=status.HTTP_302_FOUND)
        return response


@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> RedirectResponse:
    user = select_user(form_data.username)
    if user is None:
        response = RedirectResponse(url='/?wrong_cred=true', status_code=status.HTTP_302_FOUND)
        return response
    if not pwd_context.verify(form_data.password, user.hashed_password):
        response = RedirectResponse(url='/?wrong_cred=true', status_code=status.HTTP_302_FOUND)
        return response
    url = f'/weather/?city={user.city}'
    response = RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
    x = str(uuid4())
    response.set_cookie("token", value=x)
    r.set(x, user.username, ex=3600)
    return response


@app.post("/register")
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> RedirectResponse:
    user = select_user(form_data.username)
    if user:
        response = RedirectResponse(url='/?user_exists=true', status_code=status.HTTP_302_FOUND)
        return response
    with Session() as session:
        session.add(User(username=form_data.username, hashed_password=pwd_context.hash(form_data.password)))
        session.commit()
    url = f'/weather/'
    response = RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
    x = str(uuid4())
    response.set_cookie("token", value=x)
    r.set(x, form_data.username, ex=3600)
    return response


@app.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    response = RedirectResponse(url='/', status_code=status.HTTP_302_FOUND)
    response.set_cookie("token", value='0', expires=1)
    return response


if __name__ == '__main__':
    uvicorn.run(app, host='localhost', port=3000)

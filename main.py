from typing import Optional
import uvicorn
import requests
from fastapi import FastAPI, Request, Form, status, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from uuid import uuid4
from passlib.context import CryptContext

# Users
#     values('uep', 'loveuep')
#     values('burak', 'ziemniak')

TOKENS = []

app = FastAPI()
app.mount("/pics", StaticFiles(directory="pics"), name="pics")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

templates = Jinja2Templates(directory="templates")

print(pwd_context.hash('loveuep'))
print(pwd_context.hash('ziemniak'))

# uvicorn main:app --reload


class UserAuthorization:
    async def __call__(self, request: Request):
        token = request.cookies.get("token")
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Najpierw się zaloguj")
        token_in_base = False
        for i in range(len(TOKENS)):
            if token in TOKENS[i]:
                token_in_base = True
        if not token_in_base:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Najpierw się zaloguj")
        pass


class User(BaseModel):
    username: str
    city: Optional[str] = None


class UserInDB(User):
    hashed_password: str


def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Exception as e:
        print(e)
    return conn


CONN = create_connection('users.sqlite')


def select_user(username):
    cur = CONN.cursor()
    cur.execute(f"SELECT * FROM users WHERE username='{username}'")
    row = cur.fetchall()
    if len(row) > 0:
        user_dict = {
            "username": row[0][0],
            "hashed_password": row[0][1],
            "city": row[0][2],
        }
        user = UserInDB(**user_dict)
        return user
    return None


def get_weather(city):
    city_call = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid=adf0fda1db34d68d7073d8d88749962c'
    r = requests.get(city_call)
    weather_json = r.json()
    weather_type = weather_json['weather'][0]['main']
    humidity = weather_json['main']['humidity']
    pressure = weather_json['main']['pressure']
    temp_k = weather_json['main']['temp']
    temp_c = round(temp_k - 273.15, 2)
    name = weather_json['name']
    return weather_type, humidity, pressure, temp_c, name


@app.get("/", response_class=HTMLResponse)
async def root(request: Request, wrong_cred: bool = False):
    x = templates.TemplateResponse("index.html", {"request": request, "wrong_cred": wrong_cred})
    return x


@app.get("/weather", response_class=HTMLResponse, dependencies=[Depends(UserAuthorization())])
async def weather(request: Request, city: str = 'Poznań', not_found: bool = False):
    weather_type, humidity, pressure, temp, name = get_weather(city)
    dic = {"request": request, "weather_type": weather_type, 'temp': temp, "humidity": humidity, "pressure": pressure,
           "city": name, "not_found": not_found}
    x = templates.TemplateResponse("weather.html", dic)
    return x


def change_default(city, token):
    user = UserInDB
    for i in range(len(TOKENS)):
        if token in TOKENS[i]:
            user = TOKENS[i][1]
    cur = CONN.cursor()
    cur.execute(f"UPDATE users SET city = '{city}' WHERE username = '{user.username}'")
    CONN.commit()
    pass


@app.post("/weather", dependencies=[Depends(UserAuthorization())])
async def change_city(request: Request, city: str = Form(...), old_city: str = Form(...)):
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
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
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
    TOKENS.append([x, user])
    return response


@app.post("/logout")
async def logout(request: Request):
    response = RedirectResponse(url='/', status_code=status.HTTP_302_FOUND)
    response.set_cookie("token", value='0', expires=1)
    return response


if __name__ == '__main__':
    uvicorn.run(app, host='localhost', port=8000)
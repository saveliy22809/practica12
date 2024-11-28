from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, Client,Product,CartItem
from sqlalchemy.orm import relationship
import bcrypt

# Инициализация базы данных
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Подключение статических файлов и шаблонов
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Зависимость для подключения к базе данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/menu", response_class=HTMLResponse)
async def menu(request: Request, db: Session = Depends(get_db)):
    menu_items = db.query(Product).all()

    return templates.TemplateResponse("menu.html", {"request": request, "menu_items": menu_items})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: str = Form(...),
    gender: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    client = Client(
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        gender=gender,
        email=email,
        hashed_password=hashed_password.decode("utf-8"),
    )
    try:
        db.add(client)
        db.commit()
        return RedirectResponse("/", status_code=303)
    except Exception as e:
        print(e)
        error_message = {"message": 'Такой пользователь уже существует'}
        return templates.TemplateResponse("register.html", {"request": request, "error_message": error_message})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(Client.email == email).first()

    if not client or not bcrypt.checkpw(password.encode("utf-8"), client.hashed_password.encode("utf-8")):
        error_message = "Логин или пароль неверны"
        return templates.TemplateResponse(
            "login.html", {"request": request, "error_message": error_message}
        )

    # Создаем cookie с ролью пользователя
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(key="user_email", value=email, httponly=True)
    response.set_cookie(key="user_role", value=client.role, httponly=True)  # Устанавливаем роль

    return response

@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("user_email")
    return response

@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request, db: Session = Depends(get_db)):
    user_email = request.cookies.get("user_email")
    if not user_email:
        return RedirectResponse("/login")

    client = db.query(Client).filter(Client.email == user_email).first()

    if not client:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return templates.TemplateResponse("profile.html", {"request": request, "client": client})

# CRUD операции

@app.get("/profile/edit", response_class=HTMLResponse)
async def edit_profile_page(request: Request, db: Session = Depends(get_db)):
    user_email = request.cookies.get("user_email")
    if not user_email:
        return RedirectResponse("/login")

    # Ищем пользователя по email
    client = db.query(Client).filter(Client.email == user_email).first()

    if not client:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Отправляем данные на страницу редактирования
    return templates.TemplateResponse("profile_edit.html", {"request": request, "client": client})

@app.post("/profile/edit", response_class=HTMLResponse)
async def edit_profile(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: str = Form(...),
    gender: str = Form(...),
    db: Session = Depends(get_db),
):
    user_email = request.cookies.get("user_email")
    if not user_email:
        return RedirectResponse("/login")

    # Ищем пользователя по email
    client = db.query(Client).filter(Client.email == user_email).first()

    if not client:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Обновляем данные пользователя, не изменяя email
    client.first_name = first_name
    client.last_name = last_name
    client.phone = phone
    client.gender = gender

    try:
        db.commit()
        return RedirectResponse("/profile", status_code=303)
    except Exception as e:
        print(e)
        error_message = {"message": "Ошибка при обновлении данных"}
        return templates.TemplateResponse("profile_edit.html", {"request": request, "client": client, "error_message": error_message})

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, db: Session = Depends(get_db)):
    user_email = request.cookies.get("user_email")
    if not user_email:
        return RedirectResponse("/login")

    client = db.query(Client).filter(Client.email == user_email).first()

    if not client:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if client.role != "admin":  # Проверка на роль администратора
        return RedirectResponse("/menu")

    # Получаем все продукты и пользователей
    products = db.query(Product).all()
    users = db.query(Client).all()

    return templates.TemplateResponse("admin_panel.html", {"request": request, "products": products, "users": users})


@app.get("/admin/products", response_class=HTMLResponse)
async def admin_products(request: Request, db: Session = Depends(get_db)):
    user_email = request.cookies.get("user_email")
    if not user_email:
        return RedirectResponse("/login")

    client = db.query(Client).filter(Client.email == user_email).first()
    if client.role != "admin":  # Проверка на роль администратора
        return RedirectResponse("/menu")

    # Получаем все продукты
    products = db.query(Product).all()

    return templates.TemplateResponse("add_product.html", {"request": request, "products": products})

@app.post("/admin/products", response_class=HTMLResponse)
async def add_product(name: str = Form(...), price: float = Form(...), quantity: int = Form(...), db: Session = Depends(get_db)):
    product = Product(name=name, price=price, quantity_in_stock=quantity)
    db.add(product)
    db.commit()
    return RedirectResponse("/admin/products", status_code=303)

@app.post("/admin/update_product_quantity/{product_id}", response_class=HTMLResponse)
async def update_product_quantity(product_id: int, quantity: int = Form(...), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product:
        product.quantity_in_stock = quantity
        db.commit()
    return RedirectResponse("/admin/products", status_code=303)
@app.get("/admin/delete_product/{product_id}", response_class=HTMLResponse)
async def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product:
        db.delete(product)
        db.commit()
    return RedirectResponse("/admin/products", status_code=303)

@app.get("/admin/users", response_class=HTMLResponse)
async def view_users(request: Request, db: Session = Depends(get_db)):
    user_email = request.cookies.get("user_email")
    if not user_email:
        return RedirectResponse("/login")

    client = db.query(Client).filter(Client.email == user_email).first()

    if not client:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if client.role != "admin":
        return RedirectResponse("/menu")

    users = db.query(Client).all()
    return templates.TemplateResponse("view_users.html", {"request": request, "users": users})

@app.post("/add_to_cart/{product_id}")
async def add_to_cart(request: Request,product_id: int,quantity: int = Form(...),db: Session = Depends(get_db)
):
    user_email = request.cookies.get("user_email")  # Получаем email пользователя из cookie
    if not user_email:
        return RedirectResponse("/login")

    user = db.query(Client).filter(Client.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Продукт не найден")

    if product.quantity_in_stock < quantity:
        raise HTTPException(status_code=400, detail="Недостаточно товара в наличии")

    # Проверяем, есть ли уже такой товар в корзине пользователя
    cart_item = db.query(CartItem).filter(CartItem.product_id == product_id, CartItem.user_id == user.id).first()

    if cart_item:
        cart_item.quantity += quantity  # Если товар уже в корзине, увеличиваем количество
    else:
        cart_item = CartItem(product_id=product_id, user_id=user.id, quantity=quantity)
        db.add(cart_item)

    product.quantity_in_stock -= quantity  # Уменьшаем количество товара на складе
    db.commit()
    return RedirectResponse("/cart", status_code=303)

@app.get("/cart", response_class=HTMLResponse)
async def cart(request: Request, db: Session = Depends(get_db)):
    user_email = request.cookies.get("user_email")
    if not user_email:
        return RedirectResponse("/login")

    user = db.query(Client).filter(Client.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Получаем все товары в корзине конкретного пользователя
    cart_items = db.query(CartItem).join(Product).filter(CartItem.user_id == user.id).all()
    total_price = sum(item.product.price * item.quantity for item in cart_items)
    return templates.TemplateResponse("cart.html", {"request": request, "cart_items": cart_items, "total_price": total_price})

@app.post("/remove_from_cart/{cart_item_id}")
async def remove_from_cart(cart_item_id: int, request: Request, db: Session = Depends(get_db)):
    user_email = request.cookies.get("user_email")
    if not user_email:
        return RedirectResponse("/login")

    user = db.query(Client).filter(Client.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    cart_item = db.query(CartItem).filter(CartItem.id == cart_item_id, CartItem.user_id == user.id).first()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Товар не найден в корзине")

    product = cart_item.product
    product.quantity_in_stock += cart_item.quantity  # Возвращаем количество товара в склад
    db.delete(cart_item)
    db.commit()

    return RedirectResponse("/cart", status_code=303)
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Client(Base):
    __tablename__ = 'clients'

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="admin")

    # Связь с корзиной
    cart_items = relationship("CartItem", back_populates="user")


class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    quantity_in_stock = Column(Integer, default=0)

    # Связь с корзиной
    cart_items = relationship("CartItem", back_populates="product")


class CartItem(Base):
    __tablename__ = 'cart_items'

    id = Column(Integer, primary_key=True, index=True)

    # Внешний ключ для связи с продуктом
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)

    # Внешний ключ для связи с клиентом (пользователем)
    user_id = Column(Integer, ForeignKey('clients.id'), nullable=False)

    quantity = Column(Integer, nullable=False, default=1)

    # Связь с продуктом
    product = relationship('Product', back_populates="cart_items")

    # Связь с клиентом
    user = relationship('Client', back_populates="cart_items")
from __future__ import absolute_import

import datetime
import enum
import uuid
from decimal import Decimal
from typing import List, Optional

# fmt: off
from sqlalchemy import (
    Column,
    Date,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    func,
)
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref, column_property, composite, mapper, relationship
from sqlalchemy.sql.type_api import TypeEngine

from sqlalchemy.orm import declarative_base

from graphene_sqlalchemy.tests.utils import wrap_select_func
from graphene_sqlalchemy.utils import (
    SQL_VERSION_HIGHER_EQUAL_THAN_1_4,
    SQL_VERSION_HIGHER_EQUAL_THAN_2,
)

# fmt: off
if SQL_VERSION_HIGHER_EQUAL_THAN_2:
    from sqlalchemy.sql.sqltypes import HasExpressionLookup  # noqa  # isort:skip
else:
    from sqlalchemy.sql.sqltypes import _LookupExpressionAdapter as HasExpressionLookup  # noqa  # isort:skip
# fmt: on

PetKind = Enum("cat", "dog", name="pet_kind")


class HairKind(enum.Enum):
    LONG = "long"
    SHORT = "short"


Base = declarative_base()

association_table = Table(
    "association",
    Base.metadata,
    Column("pet_id", Integer, ForeignKey("pets.id")),
    Column("reporter_id", Integer, ForeignKey("reporters.id")),
)


class Editor(Base):
    __tablename__ = "editors"
    editor_id = Column(Integer(), primary_key=True)
    name = Column(String(100))


class Pet(Base):
    __tablename__ = "pets"
    id = Column(Integer(), primary_key=True)
    name = Column(String(30))
    pet_kind = Column(PetKind, nullable=False)
    hair_kind = Column(Enum(HairKind, name="hair_kind"), nullable=False)
    reporter_id = Column(Integer(), ForeignKey("reporters.id"))
    legs = Column(Integer(), default=4)


class CompositeFullName(object):
    def __init__(self, first_name, last_name):
        self.first_name = first_name
        self.last_name = last_name

    def __composite_values__(self):
        return self.first_name, self.last_name

    def __repr__(self):
        return "{} {}".format(self.first_name, self.last_name)


class ProxiedReporter(Base):
    __tablename__ = "reporters_error"
    id = Column(Integer(), primary_key=True)
    first_name = Column(String(30), doc="First name")
    last_name = Column(String(30), doc="Last name")
    reporter_id = Column(Integer(), ForeignKey("reporters.id"))
    reporter = relationship("Reporter", uselist=False)

    # This is a hybrid property, we don't support proxies on hybrids yet
    composite_prop = association_proxy("reporter", "composite_prop")


class Reporter(Base):
    __tablename__ = "reporters"

    id = Column(Integer(), primary_key=True)
    first_name = Column(String(30), doc="First name")
    last_name = Column(String(30), doc="Last name")
    email = Column(String(), doc="Email")
    favorite_pet_kind = Column(PetKind)
    pets = relationship(
        "Pet",
        secondary=association_table,
        backref="reporters",
        order_by="Pet.id",
        lazy="selectin",
    )
    articles = relationship(
        "Article", backref=backref("reporter", lazy="selectin"), lazy="selectin"
    )
    favorite_article = relationship("Article", uselist=False, lazy="selectin")

    @hybrid_property
    def hybrid_prop_with_doc(self) -> str:
        """Docstring test"""
        return self.first_name

    @hybrid_property
    def hybrid_prop(self) -> str:
        return self.first_name

    @hybrid_property
    def hybrid_prop_str(self) -> str:
        return self.first_name

    @hybrid_property
    def hybrid_prop_int(self) -> int:
        return 42

    @hybrid_property
    def hybrid_prop_float(self) -> float:
        return 42.3

    @hybrid_property
    def hybrid_prop_bool(self) -> bool:
        return True

    @hybrid_property
    def hybrid_prop_list(self) -> List[int]:
        return [1, 2, 3]

    column_prop = column_property(
        wrap_select_func(func.cast(func.count(id), Integer)), doc="Column property"
    )

    composite_prop = composite(
        CompositeFullName, first_name, last_name, doc="Composite"
    )

    headlines = association_proxy("articles", "headline")


articles_tags_table = Table(
    "articles_tags",
    Base.metadata,
    Column("article_id", ForeignKey("articles.id")),
    Column("tag_id", ForeignKey("tags.id")),
)


class Image(Base):
    __tablename__ = "images"
    id = Column(Integer(), primary_key=True)
    external_id = Column(Integer())
    description = Column(String(30))


class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer(), primary_key=True)
    name = Column(String(30))


class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer(), primary_key=True)
    headline = Column(String(100))
    pub_date = Column(Date())
    reporter_id = Column(Integer(), ForeignKey("reporters.id"))
    readers = relationship(
        "Reader", secondary="articles_readers", back_populates="articles"
    )
    recommended_reads = association_proxy("reporter", "articles")

    # one-to-one relationship with image
    image_id = Column(Integer(), ForeignKey("images.id"), unique=True)
    image = relationship("Image", backref=backref("articles", uselist=False))

    # many-to-many relationship with tags
    tags = relationship("Tag", secondary=articles_tags_table, backref="articles")


class Reader(Base):
    __tablename__ = "readers"
    id = Column(Integer(), primary_key=True)
    name = Column(String(100))
    articles = relationship(
        "Article", secondary="articles_readers", back_populates="readers"
    )


class ArticleReader(Base):
    __tablename__ = "articles_readers"
    article_id = Column(Integer(), ForeignKey("articles.id"), primary_key=True)
    reader_id = Column(Integer(), ForeignKey("readers.id"), primary_key=True)


class ReflectedEditor(type):
    """Same as Editor, but using reflected table."""

    @classmethod
    def __subclasses__(cls):
        return []


editor_table = Table("editors", Base.metadata, autoload=True)

# TODO Remove when switching min sqlalchemy version to SQLAlchemy 1.4
if SQL_VERSION_HIGHER_EQUAL_THAN_1_4:
    Base.registry.map_imperatively(ReflectedEditor, editor_table)
else:
    mapper(ReflectedEditor, editor_table)


############################################
# The models below are mainly used in the
# @hybrid_property type inference scenarios
############################################


class ShoppingCartItem(Base):
    __tablename__ = "shopping_cart_items"

    id = Column(Integer(), primary_key=True)

    @hybrid_property
    def hybrid_prop_shopping_cart(self) -> List["ShoppingCart"]:
        return [ShoppingCart(id=1)]


class ShoppingCart(Base):
    __tablename__ = "shopping_carts"

    id = Column(Integer(), primary_key=True)

    # Standard Library types

    @hybrid_property
    def hybrid_prop_str(self) -> str:
        return self.first_name

    @hybrid_property
    def hybrid_prop_int(self) -> int:
        return 42

    @hybrid_property
    def hybrid_prop_float(self) -> float:
        return 42.3

    @hybrid_property
    def hybrid_prop_bool(self) -> bool:
        return True

    @hybrid_property
    def hybrid_prop_decimal(self) -> Decimal:
        return Decimal("3.14")

    @hybrid_property
    def hybrid_prop_date(self) -> datetime.date:
        return datetime.datetime.now().date()

    @hybrid_property
    def hybrid_prop_time(self) -> datetime.time:
        return datetime.datetime.now().time()

    @hybrid_property
    def hybrid_prop_datetime(self) -> datetime.datetime:
        return datetime.datetime.now()

    # Lists and Nested Lists

    @hybrid_property
    def hybrid_prop_list_int(self) -> List[int]:
        return [1, 2, 3]

    @hybrid_property
    def hybrid_prop_list_date(self) -> List[datetime.date]:
        return [self.hybrid_prop_date, self.hybrid_prop_date, self.hybrid_prop_date]

    @hybrid_property
    def hybrid_prop_nested_list_int(self) -> List[List[int]]:
        return [
            self.hybrid_prop_list_int,
        ]

    @hybrid_property
    def hybrid_prop_deeply_nested_list_int(self) -> List[List[List[int]]]:
        return [
            [
                self.hybrid_prop_list_int,
            ],
        ]

    # Other SQLAlchemy Instance
    @hybrid_property
    def hybrid_prop_first_shopping_cart_item(self) -> ShoppingCartItem:
        return ShoppingCartItem(id=1)

    # Other SQLAlchemy Instance with expression
    @hybrid_property
    def hybrid_prop_first_shopping_cart_item_expression(self) -> ShoppingCartItem:
        return ShoppingCartItem(id=1)

    @hybrid_prop_first_shopping_cart_item_expression.expression
    def hybrid_prop_first_shopping_cart_item_expression(cls):
        return ShoppingCartItem

    # Other SQLAlchemy Instances
    @hybrid_property
    def hybrid_prop_shopping_cart_item_list(self) -> List[ShoppingCartItem]:
        return [ShoppingCartItem(id=1), ShoppingCartItem(id=2)]

    # Self-references

    @hybrid_property
    def hybrid_prop_self_referential(self) -> "ShoppingCart":
        return ShoppingCart(id=1)

    @hybrid_property
    def hybrid_prop_self_referential_list(self) -> List["ShoppingCart"]:
        return [ShoppingCart(id=1)]

    # Optional[T]

    @hybrid_property
    def hybrid_prop_optional_self_referential(self) -> Optional["ShoppingCart"]:
        return None

    # UUIDS
    @hybrid_property
    def hybrid_prop_uuid(self) -> uuid.UUID:
        return uuid.uuid4()

    @hybrid_property
    def hybrid_prop_uuid_list(self) -> List[uuid.UUID]:
        return [
            uuid.uuid4(),
        ]

    @hybrid_property
    def hybrid_prop_optional_uuid(self) -> Optional[uuid.UUID]:
        return None


class KeyedModel(Base):
    __tablename__ = "test330"
    id = Column(Integer(), primary_key=True)
    reporter_number = Column("% reporter_number", Numeric, key="reporter_number")


############################################
# For interfaces
############################################


class Person(Base):
    id = Column(Integer(), primary_key=True)
    type = Column(String())
    name = Column(String())
    birth_date = Column(Date())

    __tablename__ = "person"
    __mapper_args__ = {
        "polymorphic_on": type,
        "with_polymorphic": "*",  # needed for eager loading in async session
    }


class NonAbstractPerson(Base):
    id = Column(Integer(), primary_key=True)
    type = Column(String())
    name = Column(String())
    birth_date = Column(Date())

    __tablename__ = "non_abstract_person"
    __mapper_args__ = {
        "polymorphic_on": type,
        "polymorphic_identity": "person",
    }


class Employee(Person):
    hire_date = Column(Date())

    __mapper_args__ = {
        "polymorphic_identity": "employee",
    }


############################################
# Custom Test Models
############################################


class CustomIntegerColumn(HasExpressionLookup, TypeEngine):
    """
    Custom Column Type that our converters don't recognize
    Adapted from sqlalchemy.Integer
    """

    """A type for ``int`` integers."""

    __visit_name__ = "integer"

    def get_dbapi_type(self, dbapi):
        return dbapi.NUMBER

    @property
    def python_type(self):
        return int

    def literal_processor(self, dialect):
        def process(value):
            return str(int(value))

        return process


class CustomColumnModel(Base):
    __tablename__ = "customcolumnmodel"

    id = Column(Integer(), primary_key=True)
    custom_col = Column(CustomIntegerColumn)


class CompositePrimaryKeyTestModel(Base):
    __tablename__ = "compositekeytestmodel"

    first_name = Column(String(30), primary_key=True)
    last_name = Column(String(30), primary_key=True)

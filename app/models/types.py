"""Shared column types matching db/schema.sql.

MySQL gets UNSIGNED integers; other engines (e.g. SQLite in tests) get plain ones.
"""
from sqlalchemy import BigInteger, Integer, SmallInteger
from sqlalchemy.dialects import mysql

BigIntPK = BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql").with_variant(Integer(), "sqlite")
BigIntFK = BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")
UInt = Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")
TinyUInt = SmallInteger().with_variant(mysql.TINYINT(unsigned=True), "mysql")

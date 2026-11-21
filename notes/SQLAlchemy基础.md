# SQLAlchemy 基础：会话、事务与项目用法

**相关知识：ORM、连接池、会话、事务、flush、标识映射、异步数据库访问**

**适用版本：JobPilot 使用的 SQLAlchemy 2.1（异步扩展 `sqlalchemy.ext.asyncio`）、PostgreSQL**

2026-11-21 整理自 T1.3 讲解。代码示例均来自 JobPilot 当前源码；「我的理解」保留我的原话并注明校准。

## 一、项目用途

SQLAlchemy 是 Python 最常用的数据库库，地位接近 Java 的 Hibernate / JPA。JobPilot 用它做三件事：

- 定义表结构（`jobpilot/db/models.py`），Alembic 按这些模型生成迁移；
- 管理连接池和会话（`jobpilot/db/session.py`、`jobpilot/main.py`）；
- 构造并执行查询（`jobpilot/db/accounts.py`、`jobpilot/services/llm_gateway.py`）。

选择它而不是像早期实验那样直接用标准库 `sqlite3`，是因为连接池、事务模板、对象与 SQL 的转换、异步访问都是通用问题，与业务无关，用成熟的库比自己写可靠。代价是要多学一层概念（会话、flush、事务边界），并跟随它的版本变化。

## 二、两层结构

| 层 | 做什么 | 项目中的例子 |
|---|---|---|
| Core（核心层） | 用 Python 构造 SQL：`select()`、`update()`、`delete()`、`func.xxx` | `accounts.py` 的查询，网关里的 `update(ModelCall)` |
| ORM（对象映射层） | 表映射成类，一行映射成对象，由会话管理对象 | `models.py` 的 `User`，`session.add(User(...))` |

两层可以混用。JobPilot 用 ORM 定义表，用 Core 风格写查询，这是 2.0 起推荐的写法。

## 三、五个核心对象（从底到顶）

| 对象 | 作用 | 项目位置 | Java 对应 |
|---|---|---|---|
| `Engine` | 连接池，整个程序共用一个 | `db/session.py` 的 `create_async_engine` | `DataSource`（HikariCP） |
| `async_sessionmaker` | 会话工厂，每次调用产生一个新会话 | `main.py` 启动时创建，存到 `app.state.db_session_factory` | `EntityManagerFactory` |
| `AsyncSession` | 一次与数据库的对话，管理事务和对象 | 接口参数 `db: DbSession`，`session_factory.begin()` | `EntityManager` |
| `Base` 与模型类 | 表结构 | `db/base.py`、`db/models.py` | `@Entity`、`@Column` |
| `select` / `update` / `delete` | 构造 SQL 语句，本身不访问数据库 | `db/accounts.py` | Criteria API / JPQL |

### 连接池

```python
# jobpilot/db/session.py
create_async_engine(database_url, pool_pre_ping=True, ...)
```

`pool_pre_ping=True`：借出连接前先检查它是否还活着，避免拿到已被数据库断开的连接。

### 会话工厂

```python
# jobpilot/main.py
app.state.db_session_factory = async_sessionmaker(engine, expire_on_commit=False)
```

`expire_on_commit=False` 的原因见第六节。

### 模型类

```python
# jobpilot/db/models.py
class User(Base):
    __tablename__ = "user_account"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    email: Mapped[str] = mapped_column(String(320))
    deletion_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
```

- `Mapped[...]` 写 Python 侧类型，**带 `| None` 表示该列可为空**，不带就是 `NOT NULL`。
- `mapped_column(...)` 写数据库侧细节：列类型、主键、默认值。
- `default=uuid4` 由 Python 生成默认值；`server_default=func.now()`（见 `db/base.py` 的 `created_at`）由数据库生成。
- `Base.metadata` 登记全部表结构；`naming_convention` 统一约束和索引的命名，Alembic 自动生成迁移时用它与数据库比较。

### 语句

```python
# jobpilot/db/accounts.py
select(User).where(func.lower(User.email) == normalize_email(email))

select(UserSession.session_id, User).join(
    User, User.user_id == UserSession.user_id
).where(UserSession.token_hash == token_hash, UserSession.expires_at > func.now())

delete(UserSession).where(UserSession.session_id == session_id)
```

`func.lower` 生成 SQL 的 `lower()`，`func.now()` 生成 `now()`。语句要交给会话执行才会访问数据库。

## 四、执行查询的三种方法

| 写法 | 返回 | 项目中的例子 |
|---|---|---|
| `await session.scalar(stmt)` | 一个值或对象，查不到为 `None` | `find_account_by_email` |
| `(await session.scalars(stmt)).all()` | 对象列表 | 测试中的 `calls_of` |
| `(await session.execute(stmt)).first()` | 一行，可含多列 | `find_login_session` 用 `row.session_id`、`row.User` 取值 |

记法：只要一个东西用 `scalar`，要一串同类东西用 `scalars`，一行里要取多列用 `execute`。

## 五、会话与事务

### 会话和事务的关系

会话是容器，事务是其中的一段工作。一个会话里可以先后有多个事务：第一次执行 SQL 时自动开始事务，`commit` 或 `rollback` 结束它，之后再执行 SQL 又开始新事务。

| | 事务 | 会话 `AsyncSession` |
|---|---|---|
| 是什么 | 一组要么全部成功、要么全部撤销的 SQL | 程序侧管理与数据库对话的对象 |
| 范围 | BEGIN 到 COMMIT / ROLLBACK | 打开到关闭，中间可有多个事务 |
| 额外职责 | | 记住 `add` 过、查出来的对象，`flush` 时生成 SQL |

### 写入的三个阶段

```python
session.add(user)        # 只记在会话里，数据库还不知道
await session.flush()    # 把 INSERT 发给数据库执行，事务未提交，其他连接看不到
await session.commit()   # 提交事务
```

`create_account` 在 `flush` 后返回，目的有两个：让唯一索引当场抛出 `IntegrityError`（`register` 转成 409），以及拿到数据库填写的值。

### 项目里的两种事务用法

**接口：一个请求一个会话，最后统一提交。**

```python
# jobpilot/api/auth.py
async def register(body: RegisterRequest, db: DbSession) -> UserOut:
    user = await create_account(db, body.email, hash_password(body.password))
    await db.commit()
```

`get_session` 为每个请求打开会话，请求结束时关闭；没有 `commit` 的修改在关闭时自动回滚。

**网关：每次记账单独开一个短事务。**

```python
# jobpilot/services/llm_gateway.py 的 _register_call
async with session_factory.begin() as session:
    session.add(ModelCall(...))
# 正常离开 with 自动 commit，抛出异常自动 rollback，最后关闭会话
```

模型调用记录与业务事务分开提交，业务回滚时已花费的调用记录不会丢失（T1.1 设计）。

### 与早期 agent-lab 的对照

早期实验（标签 `learning-phase-archive` 的 `app/main.py`）直接用标准库 `sqlite3`，手写事务控制：

```python
connection = create_connection(settings.database_path)
try:
    delete_memory_records(connection, ...)
    connection.commit()
except Exception:
    connection.rollback()
    raise
finally:
    connection.close()
```

那里的 `connection` 扮演的就是现在 `AsyncSession` 的角色。事务概念没有变，变的是写法：`async with session_factory.begin()` 把「成功提交、出错回滚、最后关闭」打包成固定模板，类似 Java 从手写 `conn.commit()` 换成 `@Transactional`。ORM 多出的一层是对象管理。

### 标识映射

同一个会话里，同一行数据只对应一个 Python 对象：

```python
# jobpilot/tests/test_account_and_runs.py
assert account is await find_account_by_email(session, "foo@x.com")
```

用的是 `is` 而不是 `==`：两次查询得到同一个对象。对应 JPA 的持久化上下文（一级缓存）。

### 名字容易混的两个 session

| | 数据库会话 `AsyncSession` | 登录 session `UserSession` |
|---|---|---|
| 是什么 | 程序与数据库的一次对话 | `user_session` 表里的一行登录记录 |
| 存在多久 | 一个请求 | 7 天 |

为减少混淆，接口函数里的数据库会话参数命名为 `db`。

## 六、异步版本的注意点

1. **访问数据库的调用都要 `await`**：`flush`、`commit`、`scalar`、`execute` 要；`session.add()` 不访问数据库，不用。
2. **为什么 `expire_on_commit=False`**：默认情况下 `commit` 后对象被标记为过期，下次读属性时自动重新查询。异步代码里读属性无法 `await`，这种隐式查询会报错。`register` 先 `commit` 再读 `user.user_id`，所以必须关闭。
3. **不能懒加载**：以后定义 `relationship` 时，异步代码不能「用到时再查」，要在查询时用 `selectinload` 等方式明确加载（T1.4 起遇到再补充）。

## 七、我的理解

> 「`AsyncSession` 其实和事务差不多吧。」

**校准：** 在当前多数接口里，一个请求只提交一次，会话和事务范围大致重合，所以这个直觉可用。但两者不是同一概念：会话是容器，可以先后包含多个事务，另外还负责对象管理。

> 「记得之前的早期 agent-lab 好像每次都是事务控制，不是 session。」

**校准：** 早期确实手写 `commit` / `rollback`，但当时的 `sqlite3.Connection` 就是在做会话的工作，只是没有 ORM、不叫 session。现在是「会话（里面包着连接）+ 自动化的事务模板」。

> 「其实就是用了外部库的工具降低成本吧。」

**校准：** 对。判断标准是：问题是否通用、自己写错的代价是否高。数据库连接与密码哈希属于通用且危险的问题，用库；简历依据检查这类 JobPilot 独有的业务规则自己写。

**待补充：** 用自己的话讲清 `scalar` / `scalars` / `execute` 的区别，以及 `flush` 与 `commit` 各自什么时候用。

## 八、误区与验证

| 误区 | 正确理解 |
|---|---|
| `where(User.email == x)` 是在比较真假 | SQLAlchemy 改写了 `==`，结果是一段 SQL 条件 |
| `where(User.deletion_requested_at is None)` | Python 的 `is` 无法改写，结果直接是 `False`。应写 `.is_(None)` |
| 忘了 `commit` 也会保存 | 请求结束关闭会话时，未提交的修改自动回滚 |
| 忘了 `await` | 得到的是未执行的协程对象，不是查询结果 |
| 改了模型数据库就变了 | 模型只是代码中的描述，改表要靠 Alembic 迁移。T1.1 冒烟时的 `relation "user_account" does not exist` 就是开发库没升级迁移，`alembic current` 与 `alembic heads` 对比即可发现 |

**已有验证：**

- `tests/test_account_and_runs.py`：并发注册大小写变体只成功一个；标识映射（`is` 断言）。
- `tests/test_call_accounting.py`：业务事务回滚后，网关独立事务写入的调用记录仍然保留。
- `tests/test_auth.py`：`register` 在 `commit` 后读取 `user.user_id`（依赖 `expire_on_commit=False`）。

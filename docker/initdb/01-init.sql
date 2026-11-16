-- 脚本开始时连接的是 POSTGRES_DB 指定的开发库。
CREATE EXTENSION IF NOT EXISTS vector;

-- 测试单独使用一个库，避免测试清理影响开发数据。
CREATE DATABASE jobpilot_test;

\connect jobpilot_test

CREATE EXTENSION IF NOT EXISTS vector;

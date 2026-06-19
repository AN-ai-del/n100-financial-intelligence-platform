PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS companies;
DROP TABLE IF EXISTS profitandloss;
DROP TABLE IF EXISTS balancesheet;
DROP TABLE IF EXISTS cashflow;
DROP TABLE IF EXISTS analysis;
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS prosandcons;
DROP TABLE IF EXISTS sectors;
DROP TABLE IF EXISTS stock_prices;
DROP TABLE IF EXISTS financial_ratios;
DROP TABLE IF EXISTS peer_groups;

CREATE TABLE companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT,
    ticker TEXT,
    industry TEXT,
    sector TEXT
);

CREATE TABLE profitandloss (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT,
    ticker TEXT,
    year INTEGER,
    revenue REAL,
    expenses REAL,
    operating_profit REAL,
    net_profit REAL,
    eps REAL
);

CREATE TABLE balancesheet (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT,
    ticker TEXT,
    year INTEGER,
    equity_capital REAL,
    reserves REAL,
    borrowings REAL,
    total_assets REAL,
    total_liabilities REAL
);

CREATE TABLE cashflow (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT,
    ticker TEXT,
    year INTEGER,
    operating_cash_flow REAL,
    investing_cash_flow REAL,
    financing_cash_flow REAL,
    net_cash_flow REAL
);

CREATE TABLE analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT,
    ticker TEXT,
    year INTEGER,
    sales_growth REAL,
    profit_growth REAL,
    roe REAL,
    roce REAL
);

CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT,
    ticker TEXT,
    document_type TEXT,
    document_url TEXT
);

CREATE TABLE prosandcons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT,
    ticker TEXT,
    type TEXT,
    description TEXT
);

CREATE TABLE sectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT,
    ticker TEXT,
    sector TEXT,
    industry TEXT
);

CREATE TABLE stock_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT,
    ticker TEXT,
    date TEXT,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,
    volume REAL
);

CREATE TABLE financial_ratios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT,
    ticker TEXT,
    year INTEGER,
    roe REAL,
    roce REAL,
    debt_to_equity REAL,
    net_profit_margin REAL,
    operating_profit_margin REAL,
    eps REAL
);

CREATE TABLE peer_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT,
    ticker TEXT,
    peer_group TEXT
);
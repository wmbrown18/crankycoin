CREATE TABLE IF NOT EXISTS blocks(
    hash CHAR(32) NOT NULL,
    prevHash CHAR(32) NOT NULL,
    merkleRoot CHAR(32) NOT NULL,
    height INTEGER NOT NULL,
    nonce INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    version INTEGER NOT NULL,
    branch INTEGER DEFAULT 0,
    PRIMARY KEY hash,
    UNIQUE (prevHash, branch) ON CONFLICT ROLLBACK
) WITHOUT ROWID;

CREATE INDEX idx_blocks_height ON blocks(height);
CREATE INDEX idx_blocks_prevHash ON blocks(prevHash);

CREATE TABLE IF NOT EXISTS transactions(
    hash CHAR(32) NOT NULL,
    src CHAR(70) NOT NULL,
    dest CHAR(70) NOT NULL,
    amount REAL NOT NULL,
    fee REAL NOT NULL,
    timestamp INTEGER NOT NULL,
    signature CHAR(32) NOT NULL,
    type INTEGER NOT NULL,
    blockHash CHAR(32) NOT NULL,
    asset CHAR(32) NOT NULL,
    data TEXT NOT NULL,
    branch INTEGER DEFAULT 0,
    prevHash CHAR(32) NOT NULL,
    blockIndex INTEGER NOT NULL,
    PRIMARY KEY (hash, branch),
    UNIQUE (prevHash, branch) ON CONFLICT ROLLBACK
) WITHOUT ROWID;

CREATE INDEX idx_transactions_src ON transactions(src);
CREATE INDEX idx_transactions_dest ON transactions(dest);
CREATE INDEX idx_transactions_blockHash ON transactions(blockHash);
CREATE INDEX idx_transactions_type_asset ON transactions(type, asset);

CREATE TABLE IF NOT EXISTS branches(
    id INTEGER PRIMARY KEY,
    currentHash CHAR(32),
    currentHeight INTEGER
);
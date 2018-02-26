CREATE TABLE IF NOT EXISTS blocks(
    hash CHAR(32) NOT NULL,
    prevHash CHAR(32) NOT NULL,
    merkleRoot CHAR(32) NOT NULL,
    height INT NOT NULL,
    nonce INT NOT NULL,
    timestamp INT NOT NULL,
    version INT NOT NULL,
    branch INT DEFAULT 0,
    PRIMARY KEY hash
);

CREATE INDEX idx_blocks_height ON blocks(height);

CREATE TABLE IF NOT EXISTS transactions(
    hash CHAR(32) NOT NULL,
    src CHAR(70) NOT NULL,
    dest CHAR(70) NOT NULL,
    amount REAL NOT NULL,
    fee REAL NOT NULL,
    timestamp INT NOT NULL,
    signature CHAR(32) NOT NULL,
    type INT NOT NULL,
    blockHash CHAR(32) NOT NULL,
    asset CHAR(32) NOT NULL,
    data TEXT NOT NULL,
    branch INT DEFAULT 0,
    prevHash CHAR(32) NOT NULL,
    PRIMARY KEY (hash, branch)
);

CREATE INDEX idx_transactions_src ON transactions(src);
CREATE INDEX idx_transactions_dest ON transactions(dest);
CREATE INDEX idx_transactions_blockHash ON transactions(blockHash);
CREATE INDEX idx_transactions_type_asset ON transactions(type, asset);
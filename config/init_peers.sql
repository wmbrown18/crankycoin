CREATE TABLE IF NOT EXISTS peers(
    host CHAR(100),
    consecutive_downtime INT
    PRIMARY KEY host
);

INSERT INTO peers (host, consecutive_downtime) VALUES ('127.0.0.1', 0);
INSERT INTO peers (host, consecutive_downtime) VALUES ('127.0.0.2', 0);
CREATE TABLE IF NOT EXISTS customers (
    customer_id   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_name  VARCHAR(100) NOT NULL,
    cnpj          CHAR(14)     NOT NULL UNIQUE,
    city          VARCHAR(60)  NOT NULL,
    state         CHAR(2)      NOT NULL,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS materials (
    material_id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    material_code       VARCHAR(20)  NOT NULL UNIQUE,
    material_name       VARCHAR(100) NOT NULL,
    material_thickness_mm  NUMERIC(5,2) NOT NULL,
    material_density_g_cm3    NUMERIC(5,2) NOT NULL,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS work_centers (
    work_center_id   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    work_center_code VARCHAR(20)  NOT NULL UNIQUE,
    work_center_name VARCHAR(100) NOT NULL,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS machines (
    machine_id        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    machine_code      VARCHAR(20)  NOT NULL UNIQUE,
    machine_name      VARCHAR(100) NOT NULL,
    work_center_id    INTEGER      NOT NULL REFERENCES work_centers(work_center_id),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS operators (
    operator_id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    operator_name   VARCHAR(100) NOT NULL,
    work_center_id  INTEGER      NOT NULL REFERENCES work_centers (work_center_id),
    operator_role   VARCHAR(30)  NOT NULL
                    CHECK (role IN ('machine_operator', 'unloader', 'welder', 'assembler', 'finisher', 'inspector')),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS routings (
    routing_id    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    routing_code  VARCHAR(20)  NOT NULL UNIQUE,
    routing_name  VARCHAR(100) NOT NULL,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS routing_steps (
    routing_step_id  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    routing_id       INTEGER     NOT NULL REFERENCES routings (routing_id),
    step_sequence    SMALLINT    NOT NULL CHECK (step_sequence > 0),
    work_center_id   INTEGER     NOT NULL REFERENCES work_centers (work_center_id),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (routing_id, step_sequence)
);
CREATE TABLE IF NOT EXISTS products (
    product_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_code    VARCHAR(20)  NOT NULL UNIQUE,
    product_name    VARCHAR(100) NOT NULL,
    material_id     INTEGER      NOT NULL REFERENCES materials (material_id),
    routing_id      INTEGER      NOT NULL REFERENCES routings (routing_id),
    product_unit_weight_kg  NUMERIC(8,3) NOT NULL CHECK (product_unit_weight_kg > 0),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

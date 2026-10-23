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
    role            VARCHAR(30)  NOT NULL
                    CHECK (role IN ('machine_operator', 'unloader', 'welder',
                                    'assembler', 'finisher', 'inspector')),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
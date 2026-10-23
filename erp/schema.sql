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
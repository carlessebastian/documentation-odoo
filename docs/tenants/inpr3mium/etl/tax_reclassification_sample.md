# Sample `p_iva_exento` agrupado por proveedor

**Fuente**: `documents/purchase.jsonl` + `documents/purchaserefund.jsonl` del dump Holded `2026-05-11`.

**Totales globales**: 111 proveedores, **2.146 docs**, **439.122,30 €** en líneas con tax key `p_iva_exento`.

**Distribución por país** (líneas con p_iva_exento):

| País | Suppliers | Docs | EUR exento líneas |
|------|----------:|-----:|------------------:|
| ES   | 44 | 780 | 210.137,86 |
| US   | 26 | 799 | 88.326,87 |
| IE   | 8 | 229 | 114.977,21 |
| DE   | 7 | 71 | 3.736,60 |
| AU   | 3 | 155 | 13.571,07 |
| CN, NL, GB, SE, LU, RO, CZ, FR, NO, PL, EE, CY, GR | 23 | 102 | 7.911,51 |
| (sin país) | 6 | 8 | 461,18 |

## Cómo usar este sample

Para cada proveedor, decidir en cuál de estas 3 cubetas cae:

- **A. Exento real Art.20** (sanidad, vales, financiero, notarial, alquileres exentos) → `0% EXEMPT OP` (id=95).
- **B. Reverse charge intracom UE** → `21% RC` (id=112).
- **C. Reverse charge extra-UE** (SaaS US/AU/HK/CN/UK/...) → `21% RC` (id=112) con flag `etl_review=True`. Fase 5.3 puede requerir crear `21% RC ExtraUE` separado.
- **D. Olvido del operador en Holded** (debería haber llevado 21% repercutido normal) → recalificar a `21% G` o el tipo correcto.

Las heurísticas en la columna **Sugerencia** son orientativas. El operador decide.

## 1. Proveedores ESPAÑOLES (44 suppliers, 780 docs, 210.137,86 €)

| # | Proveedor | País | Code/VAT | Docs | Lineas | EUR exento | Periodo | Sugerencia | Descripciones más comunes |
|--:|-----------|:----:|----------|-----:|-------:|-----------:|:-------:|-----------|---------------------------|
| 1 | CHEQUE DEUJENER S.A. | ES | A78887049 | 177 | 300 | 93,074.45 | 2018-2025 | **id=95** — Vales empleados Art.20 -> 0% EXEMPT | `COMPRAS SERVICIOS TIPO EXENTO` · `Cheque Deujener` |
| 2 | PLUXEE ESPAÑA SAU | ES | A78604113 | 21 | 24 | 20,320.00 | 2024-2026 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `Pluxee` · `Importe de tarjetas` |
| 3 | ARVAL SERVICE LEASE S.A. | ES | A81573479 | 96 | 96 | 19,156.02 | 2019-2026 | **id=95** — Renting/Leasing - revisar si exento o 21% genuino | `Arval` · `COMPRAS SERVICIOS TIPO EXENTO` |
| 4 | LYNK & CO SALES SPAIN SL | ES | B05398037 | 46 | 46 | 15,155.25 | 2022-2025 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `LYNK & CO` · `LYNK & CO (diciembre)` |
| 5 | LEASE PLAN SERVICIOS S.A. | ES | A78007473 | 54 | 59 | 14,253.74 | 2018-2022 | **id=95** — Renting/Leasing - revisar si exento o 21% genuino | `COMPRAS SERVICIOS TIPO EXENTO` · `Lease Plan` |
| 6 | QUIRON PREVENCION S.L.U. | ES | B64076482 | 72 | 83 | 7,396.87 | 2018-2026 | **id=95** — Art.20 sanidad/seguros -> 0% EXEMPT | `Quiron Prevencion` · `COMPRAS SERVICIOS TIPO EXENTO` |
| 7 | MOLDTRANS S.L. | ES | B08569089 | 77 | 80 | 7,382.83 | 2018-2022 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO EXENTO` · `Moldtrans` |
| 8 | PORTOLES CARILLA, ANA | ES | 44999256D | 11 | 11 | 5,470.67 | 2018-2019 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO EXENTO` |
| 9 | EVA MELUS FIERRO | ES | 52208721D | 11 | 11 | 4,200.00 | 2018-2019 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO EXENTO` |
| 10 | AMAZON EU S.A.R.L | ES | W0184081H | 6 | 6 | 3,315.53 | 2022-2026 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `Amazon` · `PORT-069 HP Laptop PORT-069 EliteBook 840 G11 14" Intel Core` |
| 11 | REGISTRARMARCAS, S.L | ES | B64938624 | 5 | 5 | 2,896.44 | 2022-2022 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `RegistrarMarcas` · `REGISTRAR MARCA DENOMINATIVA FARMACLOUD` |
| 12 | VUELING AIRLINES S.A. | ES | A63422141 | 28 | 32 | 2,169.16 | 2018-2025 | **id=95** — Transporte (ojo: a veces lleva IVA 10%) -> revisar | `COMPRAS SERVICIOS TIPO EXENTO` · `Vueling (Geraldine Garcia)` |
| 13 | NACEX A.R.B.94 S.L. | ES | B60686169 | 47 | 47 | 2,070.71 | 2022-2025 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `Nacex` |
| 14 | FED.FARMACEUTICA S.COOP.CL. | ES | F08173395 | 11 | 11 | 1,973.19 | 2018-2025 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO EXENTO` · `Fede` |
| 15 | ASSOCIACIO DEL CLUSTER BELLESA DE CATALUNYA | ES | G66286105 | 1 | 1 | 1,200.00 | 2018-2018 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO EXENTO` |
| 16 | JAVIER FERRER GONZALEZ | ES | 47658995M | 1 | 1 | 1,027.95 | 2019-2019 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO EXENTO` |
| 17 | AUTOMOBILS A R MOTORS SL (AR MOTORS AUTOMOBIL | ES | B08126021 | 2 | 2 | 1,000.00 | 2025-2025 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `Vehículo Geraldine (FIANZA)` |
| 18 | CODELY ENSEÑA Y ENTRETIENE, S.L | ES | B67560615 | 1 | 1 | 956.00 | 2020-2020 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO EXENTO` |
| 19 | HOTEL TABURIENTE S.L. | ES | B38460358 | 3 | 3 | 885.90 | 2018-2019 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO EXENTO` |
| 20 | A.R.B. 94 S.L. "NACEX" | ES | B60686169 | 15 | 17 | 842.85 | 2018-2026 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO EXENTO` · `Nacex` |
| 21 | AMAZON EU S.A.R.L. | ES | N1081152I | 11 | 11 | 839.70 | 2019-2021 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS BIENES TIPO EXENTO` · `COMPRAS SERVICIOS TIPO EXENTO` |
| 22 | AVIS ALQUILE UN COCHE S.A. | ES | A28152767 | 4 | 4 | 677.13 | 2018-2023 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO EXENTO` · `COMPRAS BIENES TIPO EXENTO` |
| 23 | DURAN SINDREU S.L.P. | ES | B62340716 | 3 | 10 | 661.40 | 2020-2021 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO EXENTO` · `COMPRAS BIENES TIPO EXENTO` |
| 24 | J. ISERN PATENTES Y MARCAS S.L. | ES | B62748827 | 2 | 2 | 587.12 | 2022-2022 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `Isern (Mayo)` |
| 25 | CAIXABANK S.A. | ES | A08663619 | 5 | 5 | 407.50 | 2018-2018 | **id=95** — Servicios financieros Art.20 -> 0% EXEMPT | `COMPRAS SERVICIOS TIPO EXENTO` |
| 26 | JOSEP M. BORT CALDES | ES | 46623250L | 1 | 1 | 270.00 | 2019-2019 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO EXENTO` |
| 27 | PONS IP, S.A | ES | A28750891 | 3 | 3 | 268.35 | 2023-2026 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `Pons IP` · `Tasas OEPM CI08 - Oposición contra marca nacional nº 4352087` |
| 28 | SIMFONY | ES | FR06834643579 | 1 | 1 | 237.00 | 2021-2021 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO 21%` |
| 29 | AMAZON.ES COMPRA | ES | ESW0184081H | 1 | 1 | 225.00 | 2018-2018 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO EXENTO` |
| 30 | KLM Royal Dutch Airlines, | ES | W0031001A | 1 | 1 | 215.95 | 2024-2024 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `KLM` |
| 31 | AIR EUROPA LINEAS AEREAS SAU | ES | A07129430 | 2 | 2 | 187.43 | 2018-2019 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO EXENTO` |
| 32 | RYANAIR LTED. | ES | W0071513F | 6 | 6 | 184.97 | 2018-2024 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO EXENTO` · `Ryanair (Geraldine Garcia)` |
| 33 | SARA BRAVO DE SOTO (FANTASTICA BUHARDILLA) | ES | 17749926K | 1 | 1 | 162.46 | 2023-2023 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `FANTASTICA BUHARDILLA (SARA BRAVO)` |
| 34 | PRINTCARRIER.COM GMBH | ES | DE815758704 | 2 | 2 | 112.66 | 2021-2021 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO 21%` |
| 35 | BOLETIN OFICIAL DEL ESTADO | ES | Q2811001C | 2 | 2 | 86.38 | 2020-2021 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS BIENES TIPO EXENTO` · `COMPRAS SERVICIOS TIPO EXENTO` |
| 36 | RHENUS LOGISTICS S.A.U. | ES | A08211989 | 13 | 13 | 75.16 | 2019-2021 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO EXENTO` |
| 37 | SOCIEDAD ESTATAL CORREOS Y TELEGRAFOS S.A. | ES | A83052407 | 10 | 10 | 66.08 | 2018-2018 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO EXENTO` |
| 38 | RENFE OPERADORA | ES | Q2801659J | 7 | 7 | 43.95 | 2018-2020 | **id=95** — Transporte (ojo: a veces lleva IVA 10%) -> revisar | `COMPRAS SERVICIOS TIPO EXENTO` · `COMPRAS BIENES TIPO EXENTO` |
| 39 | RENFE VIAJEROS S.M.E., S.A | ES | A86868189 | 9 | 9 | 26.60 | 2021-2024 | **id=95** — Transporte (ojo: a veces lleva IVA 10%) -> revisar | `Renfe (Carles Sebastian)` · `Renfe Viajeros` |
| 40 | MENSAT S.L. | ES | B60032869 | 1 | 1 | 19.90 | 2019-2019 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO EXENTO` |
| 41 | NOTARÍA CUZCO 3 C.B | ES | E01747294 | 2 | 2 | 17.04 | 2021-2021 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO EXENTO` |
| 42 | DIEZ ARRANZ, ANA | ES | 13102882N | 2 | 2 | 12.62 | 2021-2023 | **¿?** — ES sin tax explicito -> ¿olvido del operador 21%? o Art.20 | `COMPRAS SERVICIOS TIPO 0%` · `Notario Diez Arranz` |
| 43 | BANCO DE SANTANDER S.A. | ES | A39000013 | 5 | 5 | 3.50 | 2021-2021 | **id=95** — Servicios financieros Art.20 -> 0% EXEMPT | `COMPRAS SERVICIOS TIPO EXENTO` |
| 44 | NOTARIA DIAGONAL 550 SCP | ES | J66181579 | 1 | 1 | 2.40 | 2021-2021 | **id=95** — Servicios juridicos/notariales Art.20 -> 0% EXEMPT | `COMPRAS SERVICIOS TIPO EXENTO` |

## 2. Proveedores UE no-ES (intracomunitario sospechoso) (26 suppliers, 359 docs, 121.852,71 €)

| # | Proveedor | País | Code/VAT | Docs | Lineas | EUR exento | Periodo | Sugerencia | Descripciones más comunes |
|--:|-----------|:----:|----------|-----:|-------:|-----------:|:-------:|-----------|---------------------------|
| 1 | GOOGLE IRELAND LIMITED | IE | IE6388047V | 100 | 100 | 95,670.12 | 2018-2021 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 2 | ADOBE SYSTEMS SOFTWARE IRELAND LTD | IE | IE6364992H | 67 | 67 | 11,703.17 | 2018-2021 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 3 | MICROSOFT IRELAND OPERATIONS LTD | IE | IE8256796U | 39 | 39 | 3,247.84 | 2018-2021 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 4 | CRELLO LIMITED | CY | CY10384877E | 2 | 2 | 2,762.03 | 2021-2021 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 5 | LOGMEIN INC. | IE | IE9834481A | 7 | 7 | 2,369.78 | 2018-2020 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 6 | PINGDOM AB | SE | SE556680747401 | 35 | 36 | 1,748.68 | 2018-2020 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 7 | JETBRAINS SRO | CZ | CZ26502275 | 6 | 6 | 1,548.15 | 2019-2021 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 8 | PRINTCARRIER.COM /WINTERHAUSEN | DE | DE256458550 | 15 | 15 | 1,317.71 | 2018-2020 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` · `COMPRAS BIENES TIPO GEN.` |
| 9 | HETZNER ONLINE AG | DE | DE812871812 | 23 | 23 | 1,239.19 | 2018-2019 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 10 | LASTPASS IRELAND LIMITED | IE | IE3727972WH | 1 | 1 | 1,009.43 | 2021-2021 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 11 | PIXELZ EMEA GMBH | DE | DE283285223 | 28 | 28 | 704.70 | 2018-2020 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 12 | SOLARWINDS SOFTWARE EUROPE DAC | IE | IE9652586C | 12 | 12 | 563.40 | 2021-2021 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 13 | LYNDA.COM | IE | IE9740425P | 1 | 1 | 398.47 | 2021-2021 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 14 | CLICKMEETING SP. Z.O.O | PL | PL5842747535 | 9 | 9 | 351.00 | 2020-2021 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 15 | AMAZON EU S.A.L NIEDERLASSUNG DEUTSCHLAND | DE | DE814584193 | 2 | 2 | 301.92 | 2020-2021 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 16 | HOTEL EXE PARIS CENTRE | FR | EXE PARIS | 2 | 2 | 244.38 | 2019-2019 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 17 | DIGITAL RIVER GMBH | DE | DE194149069 | 1 | 1 | 99.50 | 2018-2018 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 18 | DIGITAL DATA SOLUTIONS, B.V. | NL | NL860388141B01 | 11 | 11 | 99.00 | 2021-2021 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 19 | USEBERRY | GR | EL801021580 | 2 | 2 | 70.56 | 2021-2021 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 20 | EGODITOR GMBH | DE | DE339674880 | 1 | 1 | 60.00 | 2021-2021 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 21 | SHUTTERSTOCK NEDERLANDS BV | NL | NL854239510B01 | 1 | 1 | 59.29 | 2018-2018 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 22 | ABN SYSTEMS INTERNATIONAL SRL | RO | N0662058G | 1 | 1 | 49.58 | 2019-2019 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 23 | USETIFUL | EE | EE102043965 | 1 | 1 | 29.90 | 2021-2021 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 24 | SLACK TECHNOLOGIES LIMITED | IE | IE3336483DH | 2 | 2 | 15.00 | 2021-2021 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 25 | APPLE DISTRIBUTION INTERNATIONAL | LU | IE9700053D | 2 | 2 | 13.89 | 2018-2018 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |
| 26 | HTML EMAIL CHECK DAVID BEDENKNECHT | DE | BEDENKNECHT | 1 | 1 | 13.58 | 2018-2018 | **id=112** — UE intracom B2B servicios -> 21% RC (revisar si era bienes) | `COMPRAS SERVICIOS TIPO 21%` |

## 3. Proveedores EXTRA-UE (SaaS / servicios) (35 suppliers, 999 docs, 102.831,55 €)

| # | Proveedor | País | Code/VAT | Docs | Lineas | EUR exento | Periodo | Sugerencia | Descripciones más comunes |
|--:|-----------|:----:|----------|-----:|-------:|-----------:|:-------:|-----------|---------------------------|
| 1 | ZENDESK INC. | US | IE98452731 | 112 | 112 | 21,758.55 | 2018-2021 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 2 | SENDGRID | US | SENDGRID | 47 | 47 | 20,935.61 | 2018-2021 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 3 | MAIL CHIMP C.O. | US | EU372008134 | 52 | 52 | 14,388.81 | 2018-2021 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 4 | ATLASSIAN PTY LTD | AU | AUEU372001951 | 100 | 100 | 12,651.24 | 2018-2021 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 5 | NEXMO INC | US |  | 126 | 126 | 10,560.00 | 2018-2021 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` · `VENTAS SERVICIOS TIPO GEN.` |
| 6 | GODADDY | US | USEU826010755 | 29 | 29 | 3,864.27 | 2018-2021 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 7 | BEE MAILUP INC | US | IDEIN453916482 | 32 | 32 | 3,270.11 | 2018-2020 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 8 | STITCH, INC | US | STITCH | 27 | 27 | 2,370.96 | 2019-2021 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 9 | BEE MAILUP INC | US | EIN453916481 | 12 | 12 | 1,833.11 | 2021-2021 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 10 | FIGMA, INC. | US | FIGMA | 20 | 20 | 1,181.16 | 2020-2021 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 11 | BLENDO APRISE INC. | US | BLENDO | 10 | 10 | 965.05 | 2018-2018 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 12 | MIRO INC FORMERLY REALTIMEBOARD | US | USEIN463921926 | 21 | 21 | 927.94 | 2020-2021 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 13 | CALENDLY LLC | US | CALENDLY | 28 | 28 | 858.55 | 2019-2021 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 14 | PLATZI INC | US | PLATZI | 15 | 15 | 752.11 | 2018-2020 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 15 | IMGIX | US | IMGIX | 50 | 50 | 604.88 | 2018-2021 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 16 | SCREENCONNECT SOFTWARE, LLC | US | SCREENCONNECT | 2 | 2 | 590.71 | 2018-2020 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 17 | ZEPLIN INC. | US | ZEPLIN | 3 | 3 | 547.66 | 2018-2020 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 18 | PADDLE.COM MARKET LTD | GB | EU372017215 | 7 | 7 | 526.73 | 2020-2021 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 19 | DATACAMP INC. | US | DATACAMP | 19 | 19 | 497.74 | 2018-2021 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 20 | IWANTMYNAME IDEEGEO GROUP LTD | AU | GST99864117 | 6 | 6 | 475.34 | 2018-2024 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 21 | BITLY INC. | US | BITLY | 14 | 14 | 452.67 | 2019-2020 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 22 | CANVA PTY LTD | AU | AN80158929938 | 49 | 49 | 444.49 | 2018-2021 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 23 | BUFFER INC | US | IRSEIN800750238 | 44 | 44 | 393.28 | 2018-2021 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 24 | PROSPERWORKS INC. | US | PROSPERWORKS | 5 | 6 | 368.64 | 2018-2018 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 25 | KAHOOT AS | NO | NO997770234 | 21 | 21 | 315.00 | 2020-2021 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 26 | AMAZON WEB SERVICES | US | LU26888617 | 47 | 47 | 275.65 | 2018-2021 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 27 | NAMECHEAP.COM | US | NAMECHEAP | 23 | 23 | 230.90 | 2018-2019 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 28 | SQUARESPACE | US | SQUARESPACE | 14 | 14 | 228.00 | 2018-2019 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 29 | UDEMY | US | 3290745GH | 10 | 10 | 222.91 | 2018-2021 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 30 | DIGITAL OCEAN | US | DIGITAL | 36 | 36 | 197.65 | 2018-2021 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 31 | PCMODDERS | GB | PCMODDERS | 1 | 1 | 63.68 | 2019-2019 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 32 | VIMEO INC. | US | VIMEO | 1 | 1 | 49.95 | 2018-2018 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 33 | SHENZEN TECOOL TRADING CO., LTD | CN | SHENZENTECOOL | 1 | 1 | 13.99 | 2019-2019 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 34 | SHENZHENRONGTUO E-COMMERCE CO LIMITED | CN | SHENZHENRONGTUO | 1 | 1 | 8.22 | 2019-2019 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 35 | SPIGEN KOREA CO., LTD | CN | SPIGEN | 1 | 1 | 7.43 | 2019-2019 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |

## 4. Sin pais (revisar individualmente) (6 suppliers, 8 docs, 461,18 €)

| # | Proveedor | País | Code/VAT | Docs | Lineas | EUR exento | Periodo | Sugerencia | Descripciones más comunes |
|--:|-----------|:----:|----------|-----:|-------:|-----------:|:-------:|-----------|---------------------------|
| 1 | MING HAO TECHNOLOGY  CO LIMITED | ?? | MING HAO | 1 | 1 | 314.04 | 2019-2019 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 2 | SHENZEN SHI JUNPINGUE WUJIN ZHIPIN YOUXIAN GO | ?? | SHENZENSHI | 2 | 2 | 50.42 | 2019-2019 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 3 | HONG KONG UGREEN LIMITED | ?? | UGREEN | 1 | 1 | 49.57 | 2019-2019 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 4 | 10GTEK TRANSCEIVERS CO., LIMITED | ?? | 10GTEK | 1 | 1 | 39.66 | 2019-2019 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 5 | HMER TRADELIMITED | ?? | HMER | 1 | 1 | 7.49 | 2019-2019 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |
| 6 | HONGKONG STAROC TECHNOLOGY CO.,LIMITED | ?? | STAROC | 2 | 2 | 0.00 | 2019-2020 | **id=112** — Extra-UE B2B SaaS/servicios -> 21% RC ExtraUE (puede requerir nuevo tax) | `COMPRAS SERVICIOS TIPO 21%` |

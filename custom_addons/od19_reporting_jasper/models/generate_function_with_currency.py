# -*- coding: utf-8 -*-
"""PostgreSQL helpers required by the ported JasperReports templates.

The legacy (Odoo 15) Jasper integration relied on two database functions and a
reporting view that shipped with ``dtr_erp_package_core``.  Odoo 19 does not
provide them, so they are re-created here - same layout, same names - so the
original ``.jrxml`` files keep working through JasperStarter without touching
the report design.

One adaptation was unavoidable: Odoo 19 stores the ``res_currency`` labels as
translated ``jsonb`` values (``{"en_US": "Baht", "th_TH": "บาท"}``) instead of
the legacy ``currency_unit_label`` / ``currency_unit_label_en`` column pair.
The two number-to-text functions therefore read the ``jsonb`` payload.
"""
from odoo import models, tools


class JasperSqlSetup(models.AbstractModel):
    _name = "od19.jasper.sql.setup"
    _description = "Jasper Reports - PostgreSQL helpers"
    _auto = False

    def init(self):
        self._create_functions()
        self._create_views()

    # --------------------------------------------------------------- helpers
    def _has_column(self, table, column):
        self.env.cr.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = %s AND column_name = %s",
            (table, column),
        )
        return bool(self.env.cr.fetchone())

    def _text_column(self, table, alias, column="name", lang="th_TH"):
        """Plain-text expression for a possibly translated column.

        Odoo 19 stores translated fields as ``jsonb`` (e.g.
        ``res_country.name``), so a bare reference would print the whole
        ``{"en_US": ..., "th_TH": ...}`` payload.  Untranslated columns are
        returned as-is.
        """
        self.env.cr.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = %s AND column_name = %s",
            (table, column),
        )
        row = self.env.cr.fetchone()
        if row and row[0] == "jsonb":
            return "%s.%s ->> '%s'" % (alias, column, lang)
        return "%s.%s" % (alias, column)

    def _partner_column(self, column):
        """``res_partner`` column reference, or ``NULL`` when absent.

        ``name_en`` / ``branch_code`` are project customisations; the reporting
        views must still build on databases where they are not installed.
        """
        if self._has_column("res_partner", column):
            return "cpartner.%s" % column
        return "NULL::varchar"

    # ------------------------------------------------------------- functions
    def _create_functions(self):
        self._create_th_function()
        self._create_en_function()

    def _create_th_function(self):
        self.env.cr.execute("""
            CREATE OR REPLACE FUNCTION convert_num_th_with_currency(val numeric, currency_id int)
            RETURNS character AS
            $BODY$
            DECLARE
            bahtTH varchar DEFAULT '';
            numberVAl integer DEFAULT 0;
            intVal varchar(50);
            decVal varchar(50);
            unit_label varchar default '';
            sub_label varchar default '';

            i integer := 0;
            iLen integer;
            BEGIN
            BEGIN
            CREATE TEMP TABLE num
            (
            Id integer,
            Text varchar(50)
            );
            INSERT INTO num VALUES (0, '');
            INSERT INTO num VALUES (1, 'หนึ่ง');
            INSERT INTO num VALUES (2, 'สอง');
            INSERT INTO num VALUES (3, 'สาม');
            INSERT INTO num VALUES (4, 'สี่');
            INSERT INTO num VALUES (5, 'ห้า');
            INSERT INTO num VALUES (6, 'หก');
            INSERT INTO num VALUES (7, 'เจ็ด');
            INSERT INTO num VALUES (8, 'แปด');
            INSERT INTO num VALUES (9, 'เก้า');
            INSERT INTO num VALUES (10, 'สิบ');
            END;

            BEGIN
            CREATE TEMP TABLE rank
            (
            Id integer,
            Text varchar(50)
            );
            INSERT INTO rank VALUES (0, '');
            INSERT INTO rank VALUES (1, 'สิบ');
            INSERT INTO rank VALUES (2, 'ร้อย');
            INSERT INTO rank VALUES (3, 'พัน');
            INSERT INTO rank VALUES (4, 'หมื่น');
            INSERT INTO rank VALUES (5, 'แสน');
            INSERT INTO rank VALUES (6, 'ล้าน');
            INSERT INTO rank VALUES (7, 'สิบ');
            INSERT INTO rank VALUES (8, 'ร้อย');
            INSERT INTO rank VALUES (9, 'พัน');
            END;

            intVal := split_part(cast(val as text), '.', 1);
            decVal := split_part(cast(val as text), '.', 2);

            select coalesce(currency_unit_label ->> 'th_TH', currency_unit_label ->> 'en_US', 'บาท'),
                   coalesce(currency_subunit_label ->> 'th_TH', currency_subunit_label ->> 'en_US', 'สตางค์')
            into unit_label, sub_label
            from res_currency
            where id = currency_id;

            IF(val = 0) THEN
            bahtTH := CONCAT('ศูนย์', unit_label, 'ถ้วน');
            ELSE
            iLen := LENGTH(intVal);

            WHILE (i < iLen) LOOP
            numberVAl := CAST(SUBSTRING(intVal, i + 1, 1) AS INTEGER);
            IF(numberVAl <> 0) THEN
            IF((i = (LENGTH(intVal) - 1)) AND (numberVAl = 1)) THEN
            IF(LENGTH(intVal) = 1) THEN
            bahtTH := CONCAT(bahtTH,'หนึ่ง');
            ELSE
            bahtTH := CONCAT(bahtTH, 'เอ็ด');
            END IF;
            ELSIF((i = (LENGTH(intVal) - 7)) AND (numberVAl = 1)) THEN
            IF(LENGTH(intVal) = 7) THEN
            bahtTH := CONCAT(bahtTH,'หนึ่ง');
            ELSE
            bahtTH := CONCAT(bahtTH, 'เอ็ด');
            END IF;
            ELSIF((i = (LENGTH(intVal) - 2)) AND (numberVAl = 2)) THEN
            bahtTH := CONCAT(bahtTH,'ยี่');
            ELSIF((i = (LENGTH(intVal) - 8)) AND (numberVAl = 2)) THEN
            bahtTH := CONCAT(bahtTH,'ยี่');
            ELSIF((i = (LENGTH(intVal) - 2)) AND (numberVAl = 1)) THEN
            bahtTH := CONCAT(bahtTH,'');
            ELSIF((i = (LENGTH(intVal) - 8)) AND (numberVAl = 1)) THEN
            bahtTH := CONCAT(bahtTH,'');
            ELSE
            bahtTH := CONCAT(bahtTH, (SELECT Text FROM num WHERE Id = numberVAl Limit 1));
            END IF;

            bahtTH := CONCAT(bahtTH, (SELECT Text FROM rank WHERE Id = ((LENGTH(intVal) - i) - 1) Limit 1));

            ELSE
            IF (i = (LENGTH(intVal) - 7)) THEN
            bahtTH := CONCAT(bahtTH,'ล้าน');
            END IF;
            END IF;
            i := i + 1;
            END LOOP;

            bahtTH := CONCAT(bahtTH, unit_label);
            IF(length(decVal) = 0) or (CAST(decVal as integer) = 0) THEN
            bahtTH := CONCAT(bahtTH, 'ถ้วน');
            ELSIF (SUBSTRING(decVal, 1, 1) = '0') THEN
            numberVAl := CAST(SUBSTRING(decVal, 2, 1) AS INTEGER);
            bahtTH := CONCAT(bahtTH, (SELECT Text FROM num WHERE Id = numberVAl Limit 1));
            bahtTH := CONCAT(bahtTH, sub_label);
            ELSE
            i := 0;
            WHILE (i < iLen) LOOP
            numberVAl := CAST(SUBSTRING(decVal, i + 1, 1) AS INTEGER);
            iLen := LENGTH(decVal);
            IF(numberVAl <> 0) THEN
            IF((i = (LENGTH(decVal) - 1)) AND (numberVAl = 1)) THEN
            bahtTH := CONCAT(bahtTH, 'เอ็ด');
            ELSIF((i = (LENGTH(decVal) - 2)) AND (numberVAl = 2)) THEN
            bahtTH := CONCAT(bahtTH, 'ยี่');
            ELSIF((i = (LENGTH(decVal) - 2)) AND (numberVAl = 1)) THEN
            bahtTH := CONCAT(bahtTH, '');
            ELSE
            bahtTH := CONCAT(bahtTH, (SELECT Text FROM num WHERE Id = numberVAl Limit 1));
            END IF;

            bahtTH := CONCAT(bahtTH, (SELECT Text FROM rank WHERE Id = ((LENGTH(decVal) - i) - 1) Limit 1));
            END IF;
            i := i + 1;
            END LOOP;
            bahtTH := CONCAT(bahtTH, sub_label);
            END IF;
            END IF;

            DROP TABLE num;
            DROP TABLE rank;
            RETURN bahtTH;
            END;
            $BODY$
            LANGUAGE plpgsql;
        """)

    def _create_en_function(self):
        self.env.cr.execute("""
            create or replace function convert_num_en_with_currency(number numeric, currency_id integer)
            returns character language plpgsql as
            $$
            declare
              num_words varchar default '';
              result_text varchar default '';
              integer_num varchar default '';

              i integer default 1;
              num integer default 0;
              num_len integer default 0 ;
              num_segment_len integer default 0 ;
              low_indx integer default 0 ;
              mid_indx integer default 0 ;

              num_text varchar default '';
              tmp_text varchar default '';
              num_segment varchar default '';
              delimeter varchar default '';

              unit_label varchar default '';
              sub_label varchar default '';

              begin
                begin
                  select coalesce(currency_unit_label ->> 'en_US', 'Baht'),
                         coalesce(currency_subunit_label ->> 'en_US', 'Satang')
                  into unit_label, sub_label
                  from res_currency
                  where id = currency_id;
                end;

                begin
                  num_words = '';

                  loop
                    result_text = '';
                    mid_indx = 0;

                    integer_num = split_part(cast(number as text), '.', i);
                    if i = 2  and length(integer_num)>2 then
                      integer_num = substring(integer_num, 1, 2);
                    end if;
                    num_len = length(integer_num);

                    while( num_len > 0 ) loop
                      tmp_text = '';
                      low_indx = 0 ;

                      num_segment = ltrim(substring(integer_num, num_len - 2, 3));
                      num_segment_len = length(num_segment) ;

                      while( num_segment_len > 0 ) loop
                        num = cast(substring(num_segment, num_segment_len, 1) as integer);
                        low_indx = low_indx + 1 ;
                        if low_indx = 2 then
                          if num = 1 then
                            num = cast(substring(num_segment, num_segment_len, 2) as integer);
                            case num
                              when 10 then num_text = 'Ten';
                              when 11 then num_text = 'Eleven';
                              when 12 then num_text = 'Twelve';
                              when 13 then num_text = 'Thirteen';
                              when 14 then num_text = 'Fourteen';
                              when 15 then num_text = 'Fifteen';
                              when 16 then num_text = 'Sixteen';
                              when 17 then num_text = 'Seventeen';
                              when 18 then num_text = 'Eighteen';
                              when 19 then num_text = 'Nineteen';
                              else num_text = '';
                            end case;
                          else
                            case num
                              when 2 then num_text = 'Twenty';
                              when 3 then num_text = 'Thirty';
                              when 4 then num_text = 'Forty';
                              when 5 then num_text = 'Fifty';
                              when 6 then num_text = 'Sixty';
                              when 7 then num_text = 'Seventy';
                              when 8 then num_text = 'Eighty';
                              when 9 then num_text = 'Ninety';
                              else num_text = '';
                            end case;
                          end if ;
                        else
                          case num
                            when 1 then num_text = 'One';
                            when 2 then num_text = 'Two';
                            when 3 then num_text = 'Three';
                            when 4 then num_text = 'Four';
                            when 5 then num_text = 'Five';
                            when 6 then num_text = 'Six';
                            when 7 then num_text = 'Seven';
                            when 8 then num_text = 'Eight';
                            when 9 then num_text = 'Nine';
                            else num_text = '';
                          end case;
                        end if;

                        case low_indx
                          when 3 then
                            if tmp_text ='' then
                              delimeter = ' Hundred ';
                            else
                              delimeter = ' Hundred and ' ;
                            end if;
                          when 2 then
                            if tmp_text ='' then
                              delimeter = '';
                            else
                              delimeter = '-' ;
                            end if;
                          else delimeter = '';
                        end case;

                        if not num_text = '' then
                          if num between 10 and 20 then
                            tmp_text = num_text;
                          else
                            tmp_text = concat(num_text, delimeter, tmp_text);
                          end if;
                        end if;

                        num_segment_len = num_segment_len - 1 ;
                      end loop;

                      case mid_indx
                        when 1 then delimeter = 'Thousand';
                        when 2 then delimeter = 'Million';
                        when 3 then delimeter = 'Billion';
                        when 4 then delimeter = 'Trillion';
                        else delimeter = '';
                      end case;

                      if not tmp_text = '' then
                        tmp_text = concat(tmp_text, ' ', delimeter);
                      end if;

                      if result_text = '' then
                        result_text = tmp_text;
                      else
                        result_text = concat(tmp_text, ' ', result_text);
                      end if;

                      mid_indx = mid_indx + 1;
                      num_len = num_len - 3;
                    end loop;

                    if i = 1 then
                      num_words = concat(result_text, ' ', unit_label);
                    else
                      if result_text = '' then
                        num_words = concat(num_words, ' Only');
                      else
                        num_words = concat(num_words, ' and ', rtrim(result_text), ' ', sub_label) ;
                      end if;
                    end if;

                    i = i + 1 ;
                    exit when i = 3 ;
                  end loop;

                  if number = 0 then
                    num_words = concat('Zero ', num_words) ;
                  end if;
                  return num_words ;
                end;
              end;

            $$;
        """)

    # ----------------------------------------------------------------- views
    def _create_views(self):
        """Reporting views consumed by the legacy ``.jrxml`` templates."""
        tools.drop_view_if_exists(self.env.cr, "company_address_header_report")
        # Odoo 19 no longer stores res_partner.display_name; fall back to name.
        company_name = (
            "cpartner.display_name"
            if self._has_column("res_partner", "display_name")
            else "cpartner.name"
        )
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW public.company_address_header_report AS
            SELECT c.id,
            %(company_name)s AS company_name_thai,
            %(name_en)s AS company_name_en,
            cpartner.vat AS company_tax_id,
            %(branch_code)s AS company_branch,
            c.logo_web AS company_logo,
            concat(cpartner.street, E'\\n',
                    cpartner.street2, ' ',
                    cpartner.city,
                    case when %(state_name)s is not null then ' จังหวัด' else '' end,
                    %(state_name)s, ' ',
                    cpartner.zip,
                    case when %(country_name)s is not null then ' ' else '' end,
                    %(country_name)s) as company_address_thai,
            NULL::varchar AS company_address_en,
            %(report_header)s AS company_heaer_report,
            %(report_footer)s AS company_footer_report,
            c.phone AS company_phone,
            NULL::varchar AS company_fax,
            ( SELECT p.email
                FROM res_partner p
                WHERE p.id = c.partner_id) AS company_email,
            ( SELECT p.website
                FROM res_partner p
                WHERE p.id = c.partner_id) AS company_website
            FROM res_company c
            INNER JOIN res_partner as cpartner on cpartner.id = c.partner_id
            LEFT JOIN res_country_state as cp on cp.id = cpartner.state_id
            LEFT JOIN res_country as cc on cc.id = cpartner.country_id
            LEFT JOIN res_currency cu ON cu.id = c.currency_id
            LEFT JOIN res_partner pn ON pn.id = c.partner_id;
        """ % {
            "company_name": company_name,
            "name_en": self._partner_column("name_en"),
            "branch_code": self._partner_column("branch_code"),
            "state_name": self._text_column("res_country_state", "cp"),
            "country_name": self._text_column("res_country", "cc"),
            "report_header": self._text_column("res_company", "c", "report_header"),
            "report_footer": self._text_column("res_company", "c", "report_footer"),
        })

-- Allow a Drive source whose OCR date was corrected to move to the corrected date atomically.
create or replace function public.replace_daeyoung_sales_date(
  p_source jsonb,
  p_rows jsonb
) returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  v_sale_date date := (p_source ->> 'sale_date')::date;
  v_file_id text := p_source ->> 'file_id';
  v_row_count integer;
begin
  if v_sale_date is null or nullif(v_file_id, '') is null then
    raise exception 'source file_id and sale_date are required';
  end if;
  if jsonb_typeof(p_rows) <> 'array' then
    raise exception 'rows must be a JSON array';
  end if;

  delete from public.daeyoung_sales_sources
  where sale_date = v_sale_date or file_id = v_file_id;
  insert into public.daeyoung_sales_sources (
    file_id, file_name, sale_date, drive_url, imported_at, row_count,
    stated_total, calculated_total, min_confidence, validation_status,
    validation_issues, wolgye_regular_closed
  ) values (
    v_file_id,
    coalesce(nullif(p_source ->> 'file_name', ''), v_file_id),
    v_sale_date,
    nullif(p_source ->> 'drive_url', ''),
    now(),
    jsonb_array_length(p_rows),
    nullif(p_source ->> 'stated_total', '')::bigint,
    coalesce((p_source ->> 'calculated_total')::bigint, 0),
    nullif(p_source ->> 'min_confidence', '')::double precision,
    p_source ->> 'validation_status',
    coalesce(array(select jsonb_array_elements_text(p_source -> 'validation_issues')), '{}'),
    coalesce((p_source ->> 'wolgye_regular_closed')::boolean, false)
  );

  insert into public.daeyoung_sales_rows (
    source_file_id, row_number, sale_date, store, tax_type, amount
  )
  select v_file_id, x.row_number, v_sale_date, x.store, x.tax_type, x.amount
  from jsonb_to_recordset(p_rows) as x(
    row_number integer, store text, tax_type text, amount bigint
  );
  get diagnostics v_row_count = row_count;
  if v_row_count <> jsonb_array_length(p_rows) then
    raise exception 'row count mismatch: expected %, inserted %',
      jsonb_array_length(p_rows), v_row_count;
  end if;
  return v_row_count;
end;
$$;

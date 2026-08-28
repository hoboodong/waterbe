-- Daeyoung daily sales extracted from Google Drive screenshots.
-- Drive images remain the evidence; OCR rows and validation state are queryable here.

create table if not exists public.daeyoung_sales_sources (
  file_id text primary key,
  file_name text not null,
  sale_date date not null unique,
  drive_url text,
  imported_at timestamptz not null default now(),
  row_count integer not null default 0 check (row_count >= 0),
  stated_total bigint,
  calculated_total bigint not null default 0,
  min_confidence double precision,
  validation_status text not null check (validation_status in ('verified', 'review_required')),
  validation_issues text[] not null default '{}',
  wolgye_regular_closed boolean not null default false
);

create table if not exists public.daeyoung_sales_rows (
  source_file_id text not null
    references public.daeyoung_sales_sources(file_id) on delete cascade,
  row_number integer not null,
  sale_date date not null,
  store text not null,
  tax_type text not null check (tax_type in ('면세', '과세')),
  amount bigint not null check (amount >= 0),
  primary key (source_file_id, row_number)
);

create index if not exists daeyoung_sales_rows_date_store_idx
  on public.daeyoung_sales_rows (sale_date, store);

alter table public.daeyoung_sales_sources enable row level security;
alter table public.daeyoung_sales_rows enable row level security;
revoke all on public.daeyoung_sales_sources from anon, authenticated;
revoke all on public.daeyoung_sales_rows from anon, authenticated;
grant select on public.daeyoung_sales_sources to service_role;
grant select on public.daeyoung_sales_rows to service_role;

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

  delete from public.daeyoung_sales_sources where sale_date = v_sale_date;
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

revoke all on function public.replace_daeyoung_sales_date(jsonb, jsonb) from public;
revoke all on function public.replace_daeyoung_sales_date(jsonb, jsonb) from anon;
revoke all on function public.replace_daeyoung_sales_date(jsonb, jsonb) from authenticated;
grant execute on function public.replace_daeyoung_sales_date(jsonb, jsonb) to service_role;

create or replace view public.daeyoung_monthly_wolgye_sales as
select
  date_trunc('month', r.sale_date)::date as sales_month,
  max(r.sale_date) as latest_sale_date,
  sum(r.amount) filter (where r.tax_type = '면세') as tax_exempt_sales,
  sum(r.amount) filter (where r.tax_type = '과세') as taxable_sales,
  sum(r.amount) as total_sales,
  count(distinct r.sale_date) as sales_days
from public.daeyoung_sales_rows r
join public.daeyoung_sales_sources s on s.file_id = r.source_file_id
where r.store = 'EM월계점'
group by 1;

revoke all on public.daeyoung_monthly_wolgye_sales from anon, authenticated;
grant select on public.daeyoung_monthly_wolgye_sales to service_role;

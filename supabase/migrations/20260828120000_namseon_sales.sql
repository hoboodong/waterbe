-- Namseon daily sales imported from Google Drive.
-- Raw Drive files remain the evidence; these tables are the queryable sales ledger.

create table if not exists public.namseon_sales_sources (
  file_id text primary key,
  file_name text not null,
  sale_date date not null unique,
  modified_time timestamptz,
  imported_at timestamptz not null default now(),
  row_count integer not null default 0 check (row_count >= 0)
);

create table if not exists public.namseon_sales_rows (
  source_file_id text not null
    references public.namseon_sales_sources(file_id) on delete cascade,
  row_number integer not null,
  sale_date date not null,
  store text not null,
  product text,
  daily_qty bigint not null default 0,
  daily_sales bigint not null default 0,
  month_qty bigint not null default 0,
  month_sales bigint not null default 0,
  is_store_total boolean not null default false,
  primary key (source_file_id, row_number)
);

create index if not exists namseon_sales_rows_date_store_idx
  on public.namseon_sales_rows (sale_date, store);

create index if not exists namseon_sales_rows_store_product_idx
  on public.namseon_sales_rows (store, product);

alter table public.namseon_sales_sources enable row level security;
alter table public.namseon_sales_rows enable row level security;

revoke all on public.namseon_sales_sources from anon, authenticated;
revoke all on public.namseon_sales_rows from anon, authenticated;
grant select on public.namseon_sales_sources to service_role;
grant select on public.namseon_sales_rows to service_role;

-- One RPC call replaces one sale date atomically. It is intentionally service-role only.
create or replace function public.replace_namseon_sales_date(
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

  delete from public.namseon_sales_sources where sale_date = v_sale_date;

  insert into public.namseon_sales_sources (
    file_id, file_name, sale_date, modified_time, imported_at, row_count
  ) values (
    v_file_id,
    coalesce(nullif(p_source ->> 'file_name', ''), v_file_id),
    v_sale_date,
    nullif(p_source ->> 'modified_time', '')::timestamptz,
    now(),
    jsonb_array_length(p_rows)
  );

  insert into public.namseon_sales_rows (
    source_file_id, row_number, sale_date, store, product,
    daily_qty, daily_sales, month_qty, month_sales, is_store_total
  )
  select
    v_file_id,
    x.row_number,
    v_sale_date,
    x.store,
    x.product,
    x.daily_qty,
    x.daily_sales,
    x.month_qty,
    x.month_sales,
    x.is_store_total
  from jsonb_to_recordset(p_rows) as x(
    row_number integer,
    store text,
    product text,
    daily_qty bigint,
    daily_sales bigint,
    month_qty bigint,
    month_sales bigint,
    is_store_total boolean
  );

  get diagnostics v_row_count = row_count;
  if v_row_count <> jsonb_array_length(p_rows) then
    raise exception 'row count mismatch: expected %, inserted %',
      jsonb_array_length(p_rows), v_row_count;
  end if;
  return v_row_count;
end;
$$;

revoke all on function public.replace_namseon_sales_date(jsonb, jsonb) from public;
revoke all on function public.replace_namseon_sales_date(jsonb, jsonb) from anon;
revoke all on function public.replace_namseon_sales_date(jsonb, jsonb) from authenticated;
grant execute on function public.replace_namseon_sales_date(jsonb, jsonb) to service_role;

create or replace view public.namseon_monthly_store_sales as
with latest_dates as (
  select date_trunc('month', sale_date)::date as sales_month, max(sale_date) as basis_date
  from public.namseon_sales_rows
  group by 1
), totals as (
  select l.sales_month, l.basis_date, r.store, max(r.month_sales) as total_sales
  from latest_dates l
  join public.namseon_sales_rows r on r.sale_date = l.basis_date
  where r.is_store_total
  group by l.sales_month, l.basis_date, r.store
), event_sales as (
  select
    l.sales_month,
    l.basis_date,
    r.store,
    coalesce(sum(r.month_sales) filter (
      where r.product like any (array[
        '%통낙지볶음%', '%갑오징어무침%', '%데친문어%', '%불맛주꾸미볶음%'
      ])
    ), 0) as event_team_sales
  from latest_dates l
  join public.namseon_sales_rows r on r.sale_date = l.basis_date
  where not r.is_store_total and r.product is not null
  group by l.sales_month, l.basis_date, r.store
)
select
  t.sales_month,
  t.basis_date,
  t.store,
  t.total_sales,
  coalesce(e.event_team_sales, 0) as event_team_sales,
  t.total_sales - coalesce(e.event_team_sales, 0) as waterbe_sales
from totals t
left join event_sales e using (sales_month, basis_date, store);

revoke all on public.namseon_monthly_store_sales from anon, authenticated;
grant select on public.namseon_monthly_store_sales to service_role;

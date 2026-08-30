-- Allow server-side operational reporting to read label print and discount records.
grant select on public.print_records_wangsimni to service_role;
grant select on public.print_records_mapo to service_role;
grant select on public.print_records_wolgye to service_role;
grant select on public.print_records_mia to service_role;
grant select on public.v_discount_records to service_role;
grant select on public.v_discount_summary_monthly to service_role;

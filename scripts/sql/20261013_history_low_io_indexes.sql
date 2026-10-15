-- Run each statement separately, outside a transaction. No business rows changed.
CREATE INDEX CONCURRENTLY IF NOT EXISTS waterbe_print_wangsimni_updated_id ON public.print_records_wangsimni (updated_at, id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS waterbe_print_mapo_updated_id ON public.print_records_mapo (updated_at, id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS waterbe_print_mia_updated_id ON public.print_records_mia (updated_at, id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS waterbe_print_wolgye_updated_id ON public.print_records_wolgye (updated_at, id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS waterbe_print_mooner_updated_id ON public.print_records_mooner (updated_at, id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS waterbe_receipts_published_operation ON public.caspi_operation_receipts (published_at, operation_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS waterbe_receipts_product_store ON public.caspi_operation_receipts (store_id) WHERE operation->>'command' IN ('read_plu','write_plu');

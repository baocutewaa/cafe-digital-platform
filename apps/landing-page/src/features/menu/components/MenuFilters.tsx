import { RotateCcw, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { CaffeineLevel, MenuCategory, ProductFilterQuery } from "@/lib/api-client";

interface MenuFiltersProps {
  categories: MenuCategory[];
  filters: ProductFilterQuery;
  searchText: string;
  onSearchTextChange: (value: string) => void;
  onUpdateFilter: (patch: Partial<ProductFilterQuery>) => void;
  onReset: () => void;
}

const PRICE_OPTIONS: Array<{ label: string; value: number | undefined }> = [
  { label: "Mọi mức giá", value: undefined },
  { label: "≤ 40.000đ", value: 40000 },
  { label: "≤ 45.000đ", value: 45000 },
  { label: "≤ 50.000đ", value: 50000 },
];

const CAFFEINE_OPTIONS: Array<{ label: string; value: CaffeineLevel | undefined }> = [
  { label: "Tất cả", value: undefined },
  { label: "Không caffeine", value: "none" },
  { label: "Nhẹ", value: "low" },
  { label: "Vừa", value: "medium" },
  { label: "Đậm", value: "high" },
];

const TASTE_OPTIONS: Array<{ label: string; value: string }> = [
  { label: "Ít đắng", value: "less_bitter" },
  { label: "Ngọt dịu", value: "sweet" },
  { label: "Béo mịn", value: "creamy" },
  { label: "Hương trái cây", value: "fruity" },
  { label: "Thanh mát", value: "refreshing" },
  { label: "Đậm vị", value: "bold" },
];

export function MenuFilters({
  categories,
  filters,
  searchText,
  onSearchTextChange,
  onUpdateFilter,
  onReset,
}: MenuFiltersProps) {
  const hasActiveFilters = Boolean(
    filters.category ||
      filters.max_price !== undefined ||
      filters.caffeine_level ||
      filters.has_milk !== undefined ||
      filters.taste_tag ||
      filters.signature !== undefined ||
      searchText.trim()
  );

  return (
    <section
      aria-label="Bộ lọc thực đơn"
      className="space-y-5 rounded-sm border border-border/80 bg-card p-5 sm:p-6"
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="relative flex-1 md:max-w-md">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchText}
            onChange={(e) => onSearchTextChange(e.target.value)}
            placeholder="Tìm theo tên món hoặc hương vị (VD: ca phe muoi, cold brew)..."
            aria-label="Tìm kiếm đồ uống"
            className="pl-9"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            size="sm"
            variant={filters.signature ? "default" : "outline"}
            onClick={() =>
              onUpdateFilter({ signature: filters.signature ? undefined : true })
            }
          >
            Chỉ Signature
          </Button>
          <Button
            type="button"
            size="sm"
            variant={filters.has_milk === false ? "default" : "outline"}
            onClick={() =>
              onUpdateFilter({ has_milk: filters.has_milk === false ? undefined : false })
            }
          >
            Không sữa bò (Dairy-free)
          </Button>
          {hasActiveFilters && (
            <Button type="button" size="sm" variant="ghost" onClick={onReset} className="gap-1.5">
              <RotateCcw className="h-3.5 w-3.5" />
              Xóa lọc
            </Button>
          )}
        </div>
      </div>

      {/* Category pills */}
      <div className="space-y-2.5">
        <p className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
          Danh mục
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant={!filters.category ? "default" : "secondary"}
            onClick={() => onUpdateFilter({ category: undefined })}
          >
            Tất cả
          </Button>
          {categories.map((cat) => (
            <Button
              key={cat.id}
              type="button"
              size="sm"
              variant={filters.category === cat.slug ? "default" : "secondary"}
              onClick={() =>
                onUpdateFilter({
                  category: filters.category === cat.slug ? undefined : cat.slug,
                })
              }
            >
              {cat.name_vi} ({cat.product_count})
            </Button>
          ))}
        </div>
      </div>

      {/* Price, Caffeine, Taste */}
      <div className="grid gap-5 border-t border-border/60 pt-5 md:grid-cols-3">
        <div className="space-y-2.5">
          <p className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
            Mức giá
          </p>
          <div className="flex flex-wrap gap-1.5">
            {PRICE_OPTIONS.map((opt) => (
              <Button
                key={opt.label}
                type="button"
                size="sm"
                variant={filters.max_price === opt.value ? "default" : "outline"}
                onClick={() => onUpdateFilter({ max_price: opt.value })}
              >
                {opt.label}
              </Button>
            ))}
          </div>
        </div>

        <div className="space-y-2.5">
          <p className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
            Mức Caffeine
          </p>
          <div className="flex flex-wrap gap-1.5">
            {CAFFEINE_OPTIONS.map((opt) => (
              <Button
                key={opt.label}
                type="button"
                size="sm"
                variant={filters.caffeine_level === opt.value ? "default" : "outline"}
                onClick={() => onUpdateFilter({ caffeine_level: opt.value })}
              >
                {opt.label}
              </Button>
            ))}
          </div>
        </div>

        <div className="space-y-2.5">
          <p className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
            Gợi ý hương vị
          </p>
          <div className="flex flex-wrap gap-1.5">
            {TASTE_OPTIONS.map((opt) => (
              <Button
                key={opt.value}
                type="button"
                size="sm"
                variant={filters.taste_tag === opt.value ? "default" : "outline"}
                onClick={() =>
                  onUpdateFilter({
                    taste_tag: filters.taste_tag === opt.value ? undefined : opt.value,
                  })
                }
              >
                {opt.label}
              </Button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

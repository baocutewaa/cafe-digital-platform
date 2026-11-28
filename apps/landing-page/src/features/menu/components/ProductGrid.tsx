import { Coffee, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ProductCard } from "@/features/menu/components/ProductCard";
import type { ProductSummary } from "@/lib/api-client";

interface ProductGridProps {
  products: ProductSummary[];
  isLoading: boolean;
  onResetFilters?: () => void;
}

export function ProductGrid({ products, isLoading, onResetFilters }: ProductGridProps) {
  if (isLoading) {
    return (
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, idx) => (
          <Card key={idx} className="overflow-hidden">
            <Skeleton className="aspect-[4/3] w-full rounded-none" />
            <div className="space-y-3 p-5">
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-6 w-3/4" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-9 w-full" />
            </div>
          </Card>
        ))}
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="rounded-sm border border-dashed border-border bg-card p-10 text-center">
        <Coffee className="mx-auto h-10 w-10 text-muted-foreground" />
        <h3 className="mt-3 font-serif text-lg font-medium">Không tìm thấy đồ uống phù hợp</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Hãy thử nới lỏng điều kiện giá, mức caffeine hoặc xóa từ khóa tìm kiếm.
        </p>
        {onResetFilters && (
          <Button variant="outline" className="mt-4 gap-2" onClick={onResetFilters}>
            <RotateCcw className="h-4 w-4" />
            Đặt lại tất cả bộ lọc
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {products.map((product) => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  );
}

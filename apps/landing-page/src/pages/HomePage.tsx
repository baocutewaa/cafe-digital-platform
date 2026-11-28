import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Coffee, MapPin, Sparkles, Tag } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { LazyImage } from "@/components/shared/LazyImage";
import { SeoHead } from "@/components/shared/SeoHead";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useChatWidget } from "@/features/chat/context/ChatWidgetContext";
import { ProductGrid } from "@/features/menu/components/ProductGrid";
import { OpeningStatusBadge } from "@/features/store/components/OpeningStatusBadge";
import { apiClient } from "@/lib/api-client";
import { formatVnd, getTimeOfDayGreeting } from "@/lib/format";
import { warmupBackend } from "@/lib/warmup";

interface TasteOption {
  id: string;
  label: string;
  paramKey: "taste_tag" | "caffeine_level" | "has_milk" | "max_price";
  paramValue: string;
  promptPhrase: string;
}

const TASTE_FINDER_OPTIONS: TasteOption[] = [
  {
    id: "less_bitter",
    label: "Ít đắng",
    paramKey: "taste_tag",
    paramValue: "less_bitter",
    promptPhrase: "ít đắng",
  },
  {
    id: "sweet",
    label: "Ngọt dịu",
    paramKey: "taste_tag",
    paramValue: "sweet",
    promptPhrase: "ngọt dịu",
  },
  {
    id: "no_caffeine",
    label: "Không caffeine",
    paramKey: "caffeine_level",
    paramValue: "none",
    promptPhrase: "không caffeine",
  },
  {
    id: "dairy_free",
    label: "Không sữa bò",
    paramKey: "has_milk",
    paramValue: "false",
    promptPhrase: "không chứa sữa bò",
  },
  {
    id: "under_45k",
    label: "Dưới 45k",
    paramKey: "max_price",
    paramValue: "45000",
    promptPhrase: "giá dưới 45.000đ",
  },
];

export function HomePage() {
  useEffect(() => {
    warmupBackend();
  }, []);

  const { openChatWithPrompt } = useChatWidget();
  const [selectedTastes, setSelectedTastes] = useState<string[]>(["less_bitter", "under_45k"]);
  const greeting = getTimeOfDayGreeting();

  const storefrontQuery = useQuery({
    queryKey: ["storefront-overview"],
    queryFn: apiClient.getStorefront,
  });

  const storesQuery = useQuery({
    queryKey: ["stores-list"],
    queryFn: apiClient.getStores,
  });

  const storefront = storefrontQuery.data;
  const stores = storesQuery.data?.items ?? [];

  const toggleTaste = (id: string) => {
    setSelectedTastes((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const buildMenuLink = () => {
    const search = new URLSearchParams();
    for (const opt of TASTE_FINDER_OPTIONS) {
      if (selectedTastes.includes(opt.id)) {
        search.set(opt.paramKey, opt.paramValue);
      }
    }
    const qs = search.toString();
    return qs ? `/menu?${qs}` : "/menu";
  };

  const buildTastePrompt = () => {
    const phrases = TASTE_FINDER_OPTIONS.filter((o) => selectedTastes.includes(o.id)).map(
      (o) => o.promptPhrase
    );
    if (phrases.length === 0) {
      return "Gợi ý giúp mình vài món Signature dễ uống tại BREW & BEAN.";
    }
    return `Gợi ý giúp mình đồ uống ${phrases.join(", ")} tại BREW & BEAN.`;
  };

  return (
    <>
      <SeoHead
        title="BREW & BEAN — Cà phê Đặc sản Vành đai Hồ Tây & Bean AI"
        description="Hệ thống quán cà phê đặc sản BREW & BEAN quanh vành đai Hồ Tây (Quận Tây Hồ, Hà Nội), menu 30 món chọn lọc từ Arabica Cầu Đất & Robusta Buôn Ma Thuột và trợ lý Bean AI."
      />

      <div className="mx-auto max-w-6xl space-y-20 px-4 pb-16 pt-6 sm:px-6 lg:pt-10">
        {/* Editorial Hero Section */}
        <section className="grid items-center gap-10 py-4 lg:grid-cols-12 lg:gap-14 lg:py-8">
          <div className="space-y-7 lg:col-span-6">
            <div className="space-y-2">
              <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-muted-foreground">
                Vành đai Hồ Tây · Quận Tây Hồ, Hà Nội
              </p>
              <p className="inline-flex items-center gap-1.5 text-xs font-medium text-accent">
                <Sparkles className="h-3.5 w-3.5" />
                {greeting.title}
              </p>
            </div>

            <h1 className="font-serif text-4xl font-medium leading-[1.08] tracking-[-0.02em] text-foreground sm:text-5xl lg:text-[3.5rem]">
              {storefront?.brand_name ?? "BREW & BEAN"}
              <span className="mt-1.5 block text-foreground/85">
                Cà phê Đặc sản &amp; Bean AI
              </span>
            </h1>

            <div className="space-y-3">
              <p className="max-w-md text-base leading-relaxed text-muted-foreground">
                {storefront?.story_summary_vi ??
                  "Hệ thống không gian cà phê đặc sản quanh vành đai Hồ Tây, Hà Nội — kết nối hạt Arabica Cầu Đất 1.650m & Robusta Buôn Ma Thuột rang vừa với đúng khẩu vị của bạn."}
              </p>
              <p className="max-w-md text-xs leading-relaxed text-muted-foreground/90">
                {greeting.suggestion}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3 pt-1">
              <Link
                to="/menu"
                className="inline-flex h-11 items-center justify-center gap-2 rounded-sm bg-primary px-6 text-[11px] font-medium uppercase tracking-[0.16em] text-primary-foreground transition-colors hover:bg-primary/90"
              >
                Khám phá Menu ({storefront?.stats.products_count ?? 30} món)
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
              <button
                type="button"
                onClick={() => openChatWithPrompt(buildTastePrompt())}
                className="inline-flex h-11 items-center justify-center gap-2 rounded-sm border border-foreground/25 bg-transparent px-6 text-[11px] font-medium uppercase tracking-[0.16em] text-foreground transition-colors hover:border-foreground hover:bg-secondary/50"
              >
                <Sparkles className="h-3.5 w-3.5 text-accent" />
                Hỏi Bean AI Barista
              </button>
            </div>
          </div>

          <div className="lg:col-span-6">
            <div className="overflow-hidden rounded-sm border border-border/70 bg-secondary/40">
              <LazyImage
                src="/images/hero/brand-hero-editorial.jpg"
                alt="BREW & BEAN Specialty Espresso Extraction"
                width={900}
                height={1125}
                priority
                className="aspect-[4/5] max-h-[560px] w-full"
              />
            </div>
          </div>
        </section>

        {/* Interactive Taste Finder */}
        <section
          aria-labelledby="taste-finder-heading"
          className="border-y border-border/80 py-10"
        >
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-3">
              <p className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                <Coffee className="h-3.5 w-3.5 text-accent" />
                Interactive Taste Finder
              </p>
              <h2
                id="taste-finder-heading"
                className="font-serif text-2xl font-medium tracking-[-0.015em] sm:text-3xl"
              >
                Chọn nhanh khẩu vị hôm nay của bạn
              </h2>
              <p className="text-sm text-muted-foreground">
                Lọc trực tiếp menu theo sở thích hoặc gửi ngay yêu cầu sang trợ lý Bean AI.
              </p>

              <div className="flex flex-wrap gap-2 pt-2">
                {TASTE_FINDER_OPTIONS.map((opt) => {
                  const active = selectedTastes.includes(opt.id);
                  return (
                    <Button
                      key={opt.id}
                      type="button"
                      size="sm"
                      variant={active ? "default" : "outline"}
                      onClick={() => toggleTaste(opt.id)}
                      aria-pressed={active}
                      className="rounded-sm text-xs"
                    >
                      {opt.label}
                    </Button>
                  );
                })}
              </div>
            </div>

            <div className="flex flex-col gap-2.5 sm:flex-row lg:flex-col">
              <Link
                to={buildMenuLink()}
                className="inline-flex h-10 items-center justify-center gap-2 rounded-sm bg-primary px-6 text-[11px] font-medium uppercase tracking-[0.14em] text-primary-foreground transition-colors hover:bg-primary/90"
              >
                Xem món phù hợp ngay
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
              <Button
                type="button"
                variant="outline"
                className="h-10 gap-2 text-[11px] uppercase tracking-[0.14em]"
                onClick={() => openChatWithPrompt(buildTastePrompt())}
              >
                <Sparkles className="h-3.5 w-3.5 text-accent" />
                Nhờ Bean AI chọn món
              </Button>
            </div>
          </div>
        </section>

        {/* Signature Drinks */}
        <section aria-labelledby="signature-heading" className="space-y-8">
          <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border/70 pb-5">
            <div className="space-y-1.5">
              <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                House Signatures
              </p>
              <h2
                id="signature-heading"
                className="font-serif text-2xl font-medium tracking-[-0.015em] sm:text-3xl"
              >
                Đồ uống Đặc trưng BREW &amp; BEAN
              </h2>
            </div>
            <Link
              to="/menu?signature=true"
              className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground transition-colors hover:text-foreground"
            >
              Xem tất cả Signature
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          {storefrontQuery.isError ? (
            <Card className="p-6 text-sm text-destructive">
              Không thể tải danh sách Signature từ API local. Hãy kiểm tra Backend FastAPI trên cổng
              8000.
            </Card>
          ) : (
            <ProductGrid
              products={storefront?.signature_products ?? []}
              isLoading={storefrontQuery.isLoading}
            />
          )}
        </section>

        {/* Brand Craft Section */}
        <section
          aria-labelledby="brand-craft-heading"
          className="grid items-center gap-10 border-y border-border/80 py-12 md:grid-cols-12"
        >
          <div className="overflow-hidden rounded-sm border border-border/70 bg-secondary/40 md:col-span-6">
            <LazyImage
              src="/images/hero/cau-dat-craft.jpg"
              alt="Hạt Arabica Cầu Đất 1.650m"
              width={1200}
              height={900}
              className="aspect-[4/3] w-full"
            />
          </div>
          <div className="space-y-5 md:col-span-6 md:pl-4">
            <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Nguồn gốc &amp; Thủ công
            </p>
            <h2
              id="brand-craft-heading"
              className="font-serif text-2xl font-medium leading-snug tracking-[-0.015em] sm:text-3xl"
            >
              Arabica Cầu Đất 1.650m &amp; Robusta Buôn Ma Thuột
            </h2>
            <p className="leading-relaxed text-muted-foreground">
              Từng mẻ hạt được rang vừa trong ngày theo hồ sơ nhiệt chuẩn để giữ trọn vị ngọt caramel
              tự nhiên, hạn chế vị khét đắng và phù hợp với cả Espresso lẫn Cold Brew ủ lạnh 18 giờ.
            </p>
            <Link
              to="/about"
              className="inline-flex h-10 items-center gap-2 rounded-sm border border-foreground/25 bg-transparent px-5 text-[11px] font-medium uppercase tracking-[0.15em] text-foreground transition-colors hover:border-foreground hover:bg-secondary/50"
            >
              Tìm hiểu câu chuyện thương hiệu
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </section>

        {/* Active Promotions Preview */}
        <section aria-labelledby="promo-preview-heading" className="space-y-8">
          <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border/70 pb-5">
            <div className="space-y-1.5">
              <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                Ưu đãi hiện có
              </p>
              <h2
                id="promo-preview-heading"
                className="font-serif text-2xl font-medium tracking-[-0.015em] sm:text-3xl"
              >
                Chương trình Khuyến mãi Nổi bật
              </h2>
            </div>
            <Link
              to="/promotions"
              className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground transition-colors hover:text-foreground"
            >
              Xem tất cả ưu đãi
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {storefrontQuery.isLoading
              ? Array.from({ length: 3 }).map((_, idx) => (
                  <Card key={idx} className="p-5">
                    <Skeleton className="mb-3 h-5 w-24" />
                    <Skeleton className="mb-2 h-6 w-full" />
                    <Skeleton className="h-14 w-full" />
                  </Card>
                ))
              : (storefront?.active_promotions ?? []).map((promo) => (
                  <Card
                    key={promo.id}
                    className="flex flex-col justify-between transition-colors hover:border-foreground/30"
                  >
                    <CardContent className="space-y-3 p-6">
                      <div className="flex items-center justify-between gap-2">
                        <Badge variant="secondary" className="gap-1">
                          <Tag className="h-3 w-3 text-accent" />
                          {promo.discount_type === "percentage"
                            ? `Giảm ${promo.discount_value}%`
                            : promo.discount_type === "fixed_amount"
                              ? `Giảm ${formatVnd(promo.discount_value)}`
                              : `Tặng ${promo.discount_value} bánh`}
                        </Badge>
                        {promo.promo_code && (
                          <span className="font-mono text-xs font-semibold tracking-wider text-foreground">
                            {promo.promo_code}
                          </span>
                        )}
                      </div>
                      <h3 className="font-serif text-lg font-medium leading-snug">
                        {promo.title_vi}
                      </h3>
                      <p className="line-clamp-3 text-sm leading-relaxed text-muted-foreground">
                        {promo.summary_vi}
                      </p>
                    </CardContent>
                    <div className="border-t border-border/60 px-6 py-3.5">
                      <Link
                        to="/promotions"
                        className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground transition-colors hover:text-foreground"
                      >
                        Xem điều kiện &amp; sao chép mã
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    </div>
                  </Card>
                ))}
          </div>
        </section>

        {/* Store Locator Preview */}
        <section aria-labelledby="stores-preview-heading" className="space-y-8">
          <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border/70 pb-5">
            <div className="space-y-1.5">
              <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                Không gian ven vành đai Hồ Tây · Hà Nội
              </p>
              <h2
                id="stores-preview-heading"
                className="font-serif text-2xl font-medium tracking-[-0.015em] sm:text-3xl"
              >
                Hệ thống Quán Cà Phê tại Tây Hồ
              </h2>
            </div>
            <Link
              to="/visit"
              className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground transition-colors hover:text-foreground"
            >
              Xem giờ mở cửa chi tiết
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {storesQuery.isLoading
              ? Array.from({ length: 3 }).map((_, idx) => (
                  <Card key={idx} className="p-5">
                    <Skeleton className="mb-3 h-5 w-28" />
                    <Skeleton className="mb-2 h-6 w-3/4" />
                    <Skeleton className="h-12 w-full" />
                  </Card>
                ))
              : stores.map((store) => (
                  <Card
                    key={store.id}
                    className="flex flex-col justify-between p-6 transition-colors hover:border-foreground/30"
                  >
                    <div className="space-y-3">
                      <OpeningStatusBadge
                        isOpenNow={store.is_open_now}
                        todayHours={store.today_hours}
                      />
                      <h3 className="font-serif text-lg font-medium">{store.name}</h3>
                      <p className="flex items-start gap-2 text-sm text-muted-foreground">
                        <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
                        <span>{store.address}</span>
                      </p>
                    </div>
                    <div className="mt-5 border-t border-border/60 pt-3.5">
                      <Link
                        to="/visit"
                        className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground transition-colors hover:text-foreground"
                      >
                        Xem lịch mở cửa &amp; tiện ích
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    </div>
                  </Card>
                ))}
          </div>
        </section>
      </div>
    </>
  );
}

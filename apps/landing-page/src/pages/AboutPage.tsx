import { ArrowRight, Coffee, Flame, Sparkles, Sprout } from "lucide-react";
import { Link } from "react-router-dom";
import { LazyImage } from "@/components/shared/LazyImage";
import { SeoHead } from "@/components/shared/SeoHead";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useChatWidget } from "@/features/chat/context/ChatWidgetContext";

const BREWING_METHODS = [
  {
    title: "Espresso Chuẩn Ý",
    badge: "9 Bar · 27 giây",
    description:
      "Chiết xuất áp suất 9 bar ở nhiệt độ 92.5°C cho lớp crema dày mịn, tôn vị caramel và hạt dẻ tự nhiên của Arabica Cầu Đất.",
  },
  {
    title: "Cold Brew Ủ Lạnh 18 Giờ",
    badge: "Giảm 65% độ axit",
    description:
      "Ngâm ủ chậm trong nước lọc lạnh 4°C suốt 18 giờ liên tục, mang lại ly cà phê êm mượt, ngọt thanh và cực kỳ dễ chịu cho dạ dày.",
  },
  {
    title: "Hand-Poured V60",
    badge: "Single Origin",
    description:
      "Pha thủ công từng nhịp nước nhỏ để khơi dậy trọn vẹn nốt hương hoa trắng, cam vàng và quả mọng của hạt cà phê thu hoạch chín đỏ.",
  },
];

export function AboutPage() {
  const { openChatWithPrompt } = useChatWidget();

  return (
    <>
      <SeoHead
        title="Câu chuyện thương hiệu — BREW & BEAN Hồ Tây"
        description="Hệ thống BREW & BEAN quanh vành đai Hồ Tây, Quận Tây Hồ, Hà Nội — hành trình hạt cà phê Arabica Cầu Đất 1.650m, Robusta Buôn Ma Thuột và 3 phương pháp pha chế."
      />

      <div className="mx-auto max-w-6xl space-y-16 px-4 py-12 sm:px-6">
        <section className="grid items-center gap-10 lg:grid-cols-12 lg:gap-14">
          <div className="space-y-6 lg:col-span-6">
            <p className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
              <Sprout className="h-3.5 w-3.5 text-accent" />
              Highland Beans · Vành đai Hồ Tây, Hà Nội
            </p>
            <h1 className="font-serif text-3xl font-medium leading-[1.12] tracking-[-0.02em] sm:text-5xl">
              Nghệ thuật Cà phê Việt bên Mặt nước Hồ Tây
            </h1>
            <p className="text-base leading-relaxed text-muted-foreground">
              BREW &amp; BEAN ra đời dọc theo vành đai Hồ Tây, Quận Tây Hồ, Hà Nội với mong muốn
              đưa những mẻ cà phê đặc sản Việt Nam — từ đồi Arabica Cầu Đất 1.650m đến vùng đất
              bazan Buôn Ma Thuột — hòa vào nhịp sống thanh tĩnh ven hồ với sự minh bạch về nguồn
              gốc, hương vị và dinh dưỡng.
            </p>
            <div className="flex flex-wrap gap-3 pt-1">
              <Link
                to="/menu"
                className="inline-flex h-11 items-center gap-2 rounded-sm bg-primary px-6 text-[11px] font-medium uppercase tracking-[0.15em] text-primary-foreground transition-colors hover:bg-primary/90"
              >
                Khám phá thực đơn
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
              <Button
                type="button"
                variant="outline"
                className="h-11 gap-2 px-5 text-[11px] uppercase tracking-[0.14em]"
                onClick={() =>
                  openChatWithPrompt(
                    "Giải thích giúp mình sự khác biệt giữa Arabica Cầu Đất và Robusta Buôn Ma Thuột tại BREW & BEAN."
                  )
                }
              >
                <Sparkles className="h-3.5 w-3.5 text-accent" />
                Hỏi Bean AI về hạt cà phê
              </Button>
            </div>
          </div>

          <div className="overflow-hidden rounded-sm border border-border/70 bg-secondary/40 lg:col-span-6">
            <LazyImage
              src="/images/hero/cau-dat-craft.jpg"
              alt="Nông trại Arabica Cầu Đất 1.650m"
              width={1200}
              height={900}
              priority
              className="aspect-[4/3] w-full"
            />
          </div>
        </section>

        <section className="grid items-center gap-10 border-y border-border/80 py-12 md:grid-cols-12">
          <div className="overflow-hidden rounded-sm border border-border/70 bg-secondary/40 md:col-span-6">
            <LazyImage
              src="/images/hero/roasting-craft-editorial.jpg"
              alt="Quy trình rang xay thủ công từng mẻ nhỏ"
              width={1200}
              height={900}
              className="aspect-[4/3] w-full"
            />
          </div>
          <div className="space-y-4 md:col-span-6 md:pl-4">
            <div className="inline-flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
              <Flame className="h-3.5 w-3.5 text-accent" />
              Small-Batch Medium Roast
            </div>
            <h2 className="font-serif text-2xl font-medium tracking-[-0.015em] sm:text-3xl">
              Triết lý Rang vừa giữ trọn vị ngọt tự nhiên
            </h2>
            <p className="leading-relaxed text-muted-foreground">
              Thay vì rang quá đậm làm mất đi hương thơm trái cây và để lại vị khét đắng, đội ngũ
              Roaster của BREW &amp; BEAN kiểm soát nhiệt độ theo từng mẻ nhỏ 12 kg. Nhờ đó, ngay
              cả người mới uống cà phê hay thích vị ít đắng đều dễ dàng cảm nhận độ êm và hậu vị
              caramel sạch.
            </p>
          </div>
        </section>

        <section className="space-y-8">
          <div className="flex flex-col justify-between gap-4 border-b border-border/70 pb-5 sm:flex-row sm:items-end">
            <div className="space-y-1.5">
              <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                Brewing Craft
              </p>
              <h2 className="font-serif text-2xl font-medium tracking-[-0.015em] sm:text-3xl">
                Ba phương pháp pha chế chủ đạo
              </h2>
            </div>
            <Link
              to="/menu?category=cold-brew"
              className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground transition-colors hover:text-foreground"
            >
              Xem dòng Cold Brew 18h
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {BREWING_METHODS.map((method) => (
              <Card key={method.title} className="transition-colors hover:border-foreground/30">
                <CardContent className="space-y-3 p-6">
                  <div className="flex items-center justify-between gap-2">
                    <Coffee className="h-5 w-5 text-accent" />
                    <Badge variant="secondary">{method.badge}</Badge>
                  </div>
                  <h3 className="font-serif text-xl font-medium">{method.title}</h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {method.description}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="overflow-hidden rounded-sm border border-border/70 bg-secondary/40">
            <LazyImage
              src="/images/hero/brand-hero-editorial.jpg"
              alt="Phương pháp pha chế Cold Brew, Espresso và V60 tại BREW & BEAN"
              width={1200}
              height={675}
              className="aspect-[21/9] w-full"
            />
          </div>
        </section>
      </div>
    </>
  );
}

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
        title="Câu chuyện thương hiệu — BREW & BEAN"
        description="Hành trình hạt cà phê Arabica Cầu Đất 1.650m và Robusta Buôn Ma Thuột, quy trình rang vừa và 3 phương pháp pha chế đặc trưng tại BREW & BEAN."
      />

      <div className="mx-auto max-w-6xl space-y-14 px-4 py-10 sm:px-6 sm:py-12">
        <section className="grid items-center gap-8 lg:grid-cols-12">
          <div className="space-y-4 lg:col-span-6">
            <Badge variant="secondary" className="gap-1.5">
              <Sprout className="h-3.5 w-3.5 text-accent" />
              From Highland Farms to Cup
            </Badge>
            <h1 className="font-serif text-3xl font-bold leading-tight sm:text-5xl">
              Nghệ thuật Cà phê Việt từ Nông trại Cao nguyên
            </h1>
            <p className="text-base leading-relaxed text-muted-foreground">
              BREW &amp; BEAN ra đời với mong muốn đưa những mẻ cà phê đặc sản Việt Nam — từ đồi
              Arabica Cầu Đất ở độ cao 1.650m đến vùng đất bazan Buôn Ma Thuột — đến gần hơn với
              nhịp sống thành thị một cách minh bạch về nguồn gốc, hương vị và dinh dưỡng.
            </p>
            <div className="flex flex-wrap gap-3 pt-2">
              <Link
                to="/menu"
                className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-5 text-sm font-medium text-primary-foreground"
              >
                Khám phá thực đơn
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Button
                type="button"
                variant="outline"
                className="gap-2"
                onClick={() =>
                  openChatWithPrompt(
                    "Giải thích giúp mình sự khác biệt giữa Arabica Cầu Đất và Robusta Buôn Ma Thuột tại BREW & BEAN."
                  )
                }
              >
                <Sparkles className="h-4 w-4 text-accent" />
                Hỏi Bean AI về hạt cà phê
              </Button>
            </div>
          </div>

          <div className="overflow-hidden rounded-3xl border shadow-sm lg:col-span-6">
            <LazyImage
              src="/images/hero/cau-dat-beans.webp"
              alt="Nông trại Arabica Cầu Đất 1.650m"
              width={1200}
              height={675}
              priority
              className="aspect-[16/10] w-full"
            />
          </div>
        </section>

        <section className="grid items-center gap-8 rounded-3xl border bg-secondary/35 p-6 sm:p-10 md:grid-cols-2">
          <div className="overflow-hidden rounded-2xl border">
            <LazyImage
              src="/images/hero/roasting-craft.webp"
              alt="Quy trình rang xay thủ công từng mẻ nhỏ"
              width={1200}
              height={675}
              className="aspect-[16/10] w-full"
            />
          </div>
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-accent">
              <Flame className="h-4 w-4" />
              Small-Batch Medium Roast
            </div>
            <h2 className="font-serif text-2xl font-bold sm:text-3xl">
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

        <section className="space-y-6">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-accent">
                Brewing Craft
              </p>
              <h2 className="font-serif text-2xl font-bold sm:text-3xl">
                Ba phương pháp pha chế chủ đạo
              </h2>
            </div>
            <Link
              to="/menu?category=cold-brew"
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-primary hover:underline"
            >
              Xem dòng Cold Brew 18h
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {BREWING_METHODS.map((method) => (
              <Card key={method.title}>
                <CardContent className="space-y-3 p-6">
                  <div className="flex items-center justify-between gap-2">
                    <Coffee className="h-5 w-5 text-primary" />
                    <Badge variant="secondary">{method.badge}</Badge>
                  </div>
                  <h3 className="font-serif text-xl font-bold">{method.title}</h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {method.description}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="overflow-hidden rounded-3xl border">
            <LazyImage
              src="/images/hero/brewing-methods.webp"
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

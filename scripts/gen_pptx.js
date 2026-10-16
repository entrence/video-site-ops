const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const { FaFire, FaPlay, FaHeart, FaChartBar, FaTv, FaStar, FaBolt } = require("react-icons/fa");
const fs = require("fs");

// ===== 配色 (Coral Energy, B站风格) =====
const C = {
  bg: "1E293B",
  bgLight: "FFF8F5",
  coral: "E64A4A",
  pink: "FB7185",
  gold: "FBBF24",
  teal: "0D9488",
  purple: "8B5CF6",
  textDark: "1E293B",
  textMid: "475569",
  textLight: "94A3B8",
  white: "FFFFFF",
  cardBg: "FFFFFF",
  border: "E2E8F0",
};

// ===== 图标渲染 =====
function iconSvg(IconComp, color, size = 256) {
  return ReactDOMServer.renderToStaticMarkup(
    React.createElement(IconComp, { color, size: String(size) })
  );
}
async function iconPng(IconComp, color, size = 256) {
  const svg = iconSvg(IconComp, color, size);
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

// ===== 图片处理: 封面转base64, 头像裁圆角 =====
async function imageToBase64(path) {
  if (!path || !fs.existsSync(path)) return null;
  const buf = fs.readFileSync(path);
  const ext = path.endsWith(".png") ? "png" : "jpeg";
  return `image/${ext};base64,${buf.toString("base64")}`;
}

async function faceToCircleBase64(path) {
  // 头像裁剪为圆形PNG (带透明背景)
  if (!path || !fs.existsSync(path)) return null;
  try {
    const buf = fs.readFileSync(path);
    // 缩放到200x200并裁圆形
    const mask = Buffer.from(
      '<svg width="200" height="200"><circle cx="100" cy="100" r="100" fill="white"/></svg>'
    );
    const out = await sharp(buf)
      .resize(200, 200, { fit: "cover" })
      .composite([{ input: mask, blend: "dest-in" }])
      .png()
      .toBuffer();
    return "image/png;base64," + out.toString("base64");
  } catch (e) {
    console.error("头像处理失败:", path, e.message);
    return null;
  }
}

// ===== 工具函数 =====
function fmtNum(n) {
  if (n >= 1e8) return (n / 1e8).toFixed(1) + "亿";
  if (n >= 1e4) return (n / 1e4).toFixed(1) + "万";
  return String(n);
}

function safePath(p) {
  // pptxgenjs addImage path 需要绝对路径
  if (!p) return null;
  return fs.existsSync(p) ? p : null;
}

// ===== 读取数据 =====
const dataPath = process.argv[2] || path.join(os.homedir(), "bilibili-daily", "data.json");
const DATA = JSON.parse(fs.readFileSync(dataPath, "utf8"));

const today = DATA.date;
const regions = DATA.regions_by_count;
const regionsPlay = DATA.regions_by_play;
const top10 = DATA.top10_heat;
const top5play = DATA.top5_play;
const top3inter = DATA.top3_interact;

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = "Hermes Agent";
  pres.title = `B站日报 ${today}`;

  // 预渲染图标
  const icons = {
    fire: await iconPng(FaFire, "#" + C.coral),
    play: await iconPng(FaPlay, "#" + C.teal),
    heart: await iconPng(FaHeart, "#" + C.pink),
    chart: await iconPng(FaChartBar, "#" + C.gold),
    tv: await iconPng(FaTv, "#" + C.white),
    star: await iconPng(FaStar, "#" + C.gold),
    bolt: await iconPng(FaBolt, "#" + C.gold),
  };

  // ============================
  // SLIDE 1: 封面 (不变)
  // ============================
  const s1 = pres.addSlide();
  s1.background = { color: C.bg };

  s1.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.coral }
  });
  s1.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 5.565, w: 10, h: 0.06, fill: { color: C.gold }
  });
  s1.addShape(pres.shapes.OVAL, {
    x: -1.2, y: 1.8, w: 3.5, h: 3.5,
    fill: { color: C.coral, transparency: 85 }
  });
  s1.addShape(pres.shapes.OVAL, {
    x: 7.8, y: -1, w: 3, h: 3,
    fill: { color: C.pink, transparency: 80 }
  });

  s1.addImage({ data: icons.tv, x: 4.5, y: 0.7, w: 0.9, h: 0.9 });

  s1.addText("B 站 日 报", {
    x: 0.5, y: 1.7, w: 9, h: 1.2,
    fontSize: 54, fontFace: "Arial Black", color: C.white,
    align: "center", charSpacing: 10
  });

  s1.addText(today, {
    x: 0.5, y: 3.0, w: 9, h: 0.6,
    fontSize: 28, fontFace: "Calibri", color: C.gold,
    align: "center", bold: true
  });

  s1.addShape(pres.shapes.LINE, {
    x: 3.5, y: 3.85, w: 3, h: 0,
    line: { color: C.coral, width: 2 }
  });

  s1.addText(`今日采样 ${DATA.total_merged} 条视频  |  覆盖 ${regions.length}+ 分区`, {
    x: 0.5, y: 4.1, w: 9, h: 0.5,
    fontSize: 16, fontFace: "Calibri", color: C.textLight,
    align: "center"
  });

  s1.addText(`数据源: 热门流 ${DATA.total_popular} 条 + 排行榜 ${DATA.total_rank} 条 → 去重 ${DATA.total_merged} 条`, {
    x: 0.5, y: 4.6, w: 9, h: 0.4,
    fontSize: 12, fontFace: "Calibri", color: C.textLight,
    align: "center"
  });

  s1.addText("Hermes Agent · 自动生成", {
    x: 0.5, y: 5.15, w: 9, h: 0.3,
    fontSize: 10, fontFace: "Calibri", color: C.textLight,
    align: "center", italic: true
  });

  // ============================
  // SLIDE 2: 分区热度排行 (不变, 柱状图+TOP5卡片)
  // ============================
  const s2 = pres.addSlide();
  s2.background = { color: C.bgLight };

  s2.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.9, fill: { color: C.bg }
  });
  s2.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0.9, w: 10, h: 0.04, fill: { color: C.coral }
  });
  s2.addImage({ data: icons.chart, x: 0.4, y: 0.22, w: 0.45, h: 0.45 });
  s2.addText("分区热度排行", {
    x: 1.0, y: 0.15, w: 5, h: 0.6,
    fontSize: 24, fontFace: "Arial Black", color: C.white, valign: "middle"
  });
  s2.addText("哪些分区今天最火?", {
    x: 6.5, y: 0.15, w: 3.2, h: 0.6,
    fontSize: 13, fontFace: "Calibri", color: C.gold,
    valign: "middle", align: "right", italic: true
  });

  const top8regions = regions.slice(0, 8);
  s2.addChart(pres.charts.BAR, [{
    name: "上榜视频数",
    labels: top8regions.map(r => r.name),
    values: top8regions.map(r => r.count),
  }], {
    x: 0.3, y: 1.15, w: 5.5, h: 4.2,
    barDir: "bar",
    chartColors: [C.coral],
    chartArea: { fill: { color: C.white }, roundedCorners: true },
    catAxisLabelColor: C.textDark,
    catAxisLabelFontFace: "Calibri",
    catAxisLabelFontSize: 11,
    valAxisLabelColor: C.textLight,
    valGridLine: { color: C.border, size: 0.5 },
    catGridLine: { style: "none" },
    showValue: true,
    dataLabelPosition: "outEnd",
    dataLabelColor: C.coral,
    dataLabelFontSize: 10,
    dataLabelFontBold: true,
    showLegend: false,
    barGapWidthPct: 40,
  });

  s2.addText("累计播放 TOP5", {
    x: 6.1, y: 1.2, w: 3.6, h: 0.4,
    fontSize: 16, fontFace: "Arial Black", color: C.textDark
  });

  const medColors = [C.coral, C.pink, C.gold, C.teal, C.purple];
  regionsPlay.slice(0, 5).forEach((r, i) => {
    const y = 1.7 + i * 0.72;
    s2.addShape(pres.shapes.RECTANGLE, {
      x: 6.1, y: y, w: 3.6, h: 0.6,
      fill: { color: C.white },
      shadow: { type: "outer", color: C.textDark, blur: 4, offset: 1, angle: 90, opacity: 0.08 }
    });
    s2.addShape(pres.shapes.RECTANGLE, {
      x: 6.1, y: y, w: 0.06, h: 0.6, fill: { color: medColors[i] }
    });
    s2.addText(`${i + 1}`, {
      x: 6.22, y: y, w: 0.35, h: 0.6,
      fontSize: 20, fontFace: "Arial Black", color: medColors[i],
      align: "center", valign: "middle"
    });
    s2.addText(r.name, {
      x: 6.6, y: y + 0.05, w: 1.8, h: 0.5,
      fontSize: 13, fontFace: "Calibri", color: C.textDark, valign: "middle", bold: true
    });
    s2.addText(fmtNum(r.play), {
      x: 8.3, y: y + 0.05, w: 1.3, h: 0.5,
      fontSize: 14, fontFace: "Calibri", color: medColors[i],
      valign: "middle", align: "right", bold: true
    });
  });

  // ============================
  // SLIDE 3: 综合热度 TOP5 (带封面+头像)
  // ============================
  const s3 = pres.addSlide();
  s3.background = { color: C.bg };

  s3.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.04, fill: { color: C.coral }
  });
  s3.addImage({ data: icons.fire, x: 0.4, y: 0.3, w: 0.45, h: 0.45 });
  s3.addText("综合热度 TOP 5", {
    x: 1.0, y: 0.25, w: 6, h: 0.55,
    fontSize: 26, fontFace: "Arial Black", color: C.white, valign: "middle"
  });
  s3.addText("播放 + 点赞×5 + 投币×10 + 收藏×3 + 分享×8 + 评论×3", {
    x: 3.5, y: 0.85, w: 6.2, h: 0.3,
    fontSize: 11, fontFace: "Calibri", color: C.textLight,
    align: "right", italic: true
  });

  // 预处理头像: 裁圆形
  const top5 = top10.slice(0, 5);
  const faceDataList = [];
  for (const v of top5) {
    const fd = await faceToCircleBase64(v.face_path);
    faceDataList.push(fd);
  }
  const coverDataList = [];
  for (const v of top5) {
    const cd = await imageToBase64(v.cover_path);
    coverDataList.push(cd);
  }

  top5.forEach((v, i) => {
    const y = 1.25 + i * 0.83;
    const isFirst = i === 0;
    const rankColor = isFirst ? C.gold : (i === 1 ? "CBD5E1" : (i === 2 ? "F59E0B" : C.textLight));

    // 卡片背景
    s3.addShape(pres.shapes.RECTANGLE, {
      x: 0.4, y: y, w: 9.2, h: 0.72,
      fill: { color: isFirst ? "2D3B52" : "283545" },
      shadow: isFirst
        ? { type: "outer", color: C.coral, blur: 8, offset: 0, angle: 90, opacity: 0.15 }
        : undefined
    });
    // 左侧排名色条
    s3.addShape(pres.shapes.RECTANGLE, {
      x: 0.4, y: y, w: 0.06, h: 0.72, fill: { color: rankColor }
    });

    // 排名数字
    s3.addText(`${i + 1}`, {
      x: 0.5, y: y, w: 0.4, h: 0.72,
      fontSize: isFirst ? 28 : 20, fontFace: "Arial Black",
      color: rankColor, align: "center", valign: "middle"
    });

    // 视频封面缩略图 (0.96 x 0.56, 16:9比例)
    const coverX = 0.95;
    const coverW = 0.96;
    const coverH = 0.56;
    const coverY = y + (0.72 - coverH) / 2;
    if (coverDataList[i]) {
      s3.addImage({
        data: coverDataList[i],
        x: coverX, y: coverY, w: coverW, h: coverH,
        sizing: { type: "cover", w: coverW, h: coverH }
      });
    } else {
      // 无封面时用色块占位
      s3.addShape(pres.shapes.RECTANGLE, {
        x: coverX, y: coverY, w: coverW, h: coverH, fill: { color: "1E293B" }
      });
    }

    // UP主头像 (圆形, 0.32 x 0.32) 放在封面右下角
    const faceSize = 0.3;
    const faceX = coverX + coverW - faceSize / 2;
    const faceY = coverY + coverH - faceSize / 2;
    // 白色底圈
    s3.addShape(pres.shapes.OVAL, {
      x: faceX - 0.02, y: faceY - 0.02, w: faceSize + 0.04, h: faceSize + 0.04,
      fill: { color: C.white }
    });
    if (faceDataList[i]) {
      s3.addImage({
        data: faceDataList[i],
        x: faceX, y: faceY, w: faceSize, h: faceSize
      });
    }

    // 标题
    s3.addText(v.title, {
      x: 2.1, y: y + 0.06, w: 4.8, h: 0.35,
      fontSize: 12, fontFace: "Calibri", color: C.white,
      bold: isFirst, valign: "middle"
    });
    // UP主名 + 分区
    s3.addText(`${v.up}  ·  ${v.region}`, {
      x: 2.1, y: y + 0.4, w: 4.8, h: 0.28,
      fontSize: 10, fontFace: "Calibri", color: C.textLight, valign: "middle"
    });

    // 热度值
    s3.addText(fmtNum(v.heat), {
      x: 7.0, y: y, w: 1.8, h: 0.72,
      fontSize: isFirst ? 24 : 18, fontFace: "Arial Black",
      color: isFirst ? C.gold : C.coral,
      align: "center", valign: "middle"
    });
    s3.addText("热度", {
      x: 8.8, y: y + 0.18, w: 0.7, h: 0.35,
      fontSize: 9, fontFace: "Calibri", color: C.textLight, valign: "middle"
    });
  });

  s3.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 5.5, w: 9.2, h: 0.08, fill: { color: C.coral, transparency: 60 }
  });

  // ============================
  // SLIDE 4: 播放量 TOP5 + 高互动率 TOP3 (带封面+头像)
  // ============================
  const s4 = pres.addSlide();
  s4.background = { color: C.bgLight };

  s4.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.9, fill: { color: C.bg }
  });
  s4.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0.9, w: 10, h: 0.04, fill: { color: C.gold }
  });
  s4.addImage({ data: icons.play, x: 0.4, y: 0.22, w: 0.45, h: 0.45 });
  s4.addText("播放量 & 互动率", {
    x: 1.0, y: 0.15, w: 5, h: 0.6,
    fontSize: 24, fontFace: "Arial Black", color: C.white, valign: "middle"
  });

  // --- 左半: 播放量 TOP5 ---
  s4.addText("▶ 播放量 TOP 5", {
    x: 0.4, y: 1.1, w: 4.6, h: 0.4,
    fontSize: 16, fontFace: "Arial Black", color: C.coral
  });

  // 预处理播放TOP5的封面和头像
  const playCovers = [], playFaces = [];
  for (const v of top5play) {
    playCovers.push(await imageToBase64(v.cover_path));
    playFaces.push(await faceToCircleBase64(v.face_path));
  }

  const playColors = [C.coral, C.pink, C.gold, C.teal, C.purple];
  top5play.forEach((v, i) => {
    const y = 1.55 + i * 0.82;

    // 卡片
    s4.addShape(pres.shapes.RECTANGLE, {
      x: 0.4, y: y, w: 4.6, h: 0.72,
      fill: { color: C.white },
      shadow: { type: "outer", color: C.textDark, blur: 4, offset: 1, angle: 90, opacity: 0.08 }
    });
    // 色条
    s4.addShape(pres.shapes.RECTANGLE, {
      x: 0.4, y: y, w: 0.06, h: 0.72, fill: { color: playColors[i] }
    });
    // 排名
    s4.addText(`${i + 1}`, {
      x: 0.48, y: y, w: 0.3, h: 0.72,
      fontSize: 18, fontFace: "Arial Black", color: playColors[i],
      align: "center", valign: "middle"
    });

    // 封面缩略图
    const coverX = 0.82;
    const coverW = 0.72;
    const coverH = 0.54;
    const coverY = y + (0.72 - coverH) / 2;
    if (playCovers[i]) {
      s4.addImage({
        data: playCovers[i],
        x: coverX, y: coverY, w: coverW, h: coverH,
        sizing: { type: "cover", w: coverW, h: coverH }
      });
    } else {
      s4.addShape(pres.shapes.RECTANGLE, {
        x: coverX, y: coverY, w: coverW, h: coverH, fill: { color: C.border }
      });
    }

    // 头像 (圆形)
    const faceSize = 0.26;
    const faceX = coverX + coverW - faceSize / 2;
    const faceY = coverY + coverH - faceSize / 2;
    s4.addShape(pres.shapes.OVAL, {
      x: faceX - 0.02, y: faceY - 0.02, w: faceSize + 0.04, h: faceSize + 0.04,
      fill: { color: C.white }
    });
    if (playFaces[i]) {
      s4.addImage({ data: playFaces[i], x: faceX, y: faceY, w: faceSize, h: faceSize });
    }

    // 标题
    s4.addText(v.title, {
      x: 1.65, y: y + 0.06, w: 2.1, h: 0.32,
      fontSize: 10, fontFace: "Calibri", color: C.textDark, bold: true, valign: "middle"
    });
    // UP + 分区
    s4.addText(`${v.up} · ${v.region}`, {
      x: 1.65, y: y + 0.38, w: 2.1, h: 0.26,
      fontSize: 8, fontFace: "Calibri", color: C.textMid, valign: "middle"
    });
    // 播放量大字
    s4.addText(fmtNum(v.view), {
      x: 3.7, y: y, w: 1.25, h: 0.72,
      fontSize: 16, fontFace: "Arial Black", color: playColors[i],
      align: "right", valign: "middle"
    });
  });

  // --- 右半: 高互动率 TOP3 ---
  s4.addText("♥ 高互动率 TOP 3", {
    x: 5.3, y: 1.1, w: 4.3, h: 0.4,
    fontSize: 16, fontFace: "Arial Black", color: C.pink
  });
  s4.addText("互动率 = (赞+币+藏+评+分享) / 播放", {
    x: 5.3, y: 1.5, w: 4.3, h: 0.25,
    fontSize: 9, fontFace: "Calibri", color: C.textMid, italic: true
  });

  // 预处理互动率TOP3的封面和头像
  const interCovers = [], interFaces = [];
  for (const v of top3inter) {
    interCovers.push(await imageToBase64(v.cover_path));
    interFaces.push(await faceToCircleBase64(v.face_path));
  }

  top3inter.forEach((v, i) => {
    const y = 1.85 + i * 1.15;

    // 卡片
    s4.addShape(pres.shapes.RECTANGLE, {
      x: 5.3, y: y, w: 4.3, h: 1.0,
      fill: { color: C.white },
      shadow: { type: "outer", color: C.textDark, blur: 4, offset: 1, angle: 90, opacity: 0.08 }
    });
    // 色条
    s4.addShape(pres.shapes.RECTANGLE, {
      x: 5.3, y: y, w: 0.06, h: 1.0, fill: { color: C.pink }
    });

    // 封面缩略图
    const coverX = 5.5;
    const coverW = 0.85;
    const coverH = 0.64;
    const coverY = y + (1.0 - coverH) / 2;
    if (interCovers[i]) {
      s4.addImage({
        data: interCovers[i],
        x: coverX, y: coverY, w: coverW, h: coverH,
        sizing: { type: "cover", w: coverW, h: coverH }
      });
    } else {
      s4.addShape(pres.shapes.RECTANGLE, {
        x: coverX, y: coverY, w: coverW, h: coverH, fill: { color: C.border }
      });
    }

    // 头像
    const faceSize = 0.28;
    const faceX = coverX + coverW - faceSize / 2;
    const faceY = coverY + coverH - faceSize / 2;
    s4.addShape(pres.shapes.OVAL, {
      x: faceX - 0.02, y: faceY - 0.02, w: faceSize + 0.04, h: faceSize + 0.04,
      fill: { color: C.white }
    });
    if (interFaces[i]) {
      s4.addImage({ data: interFaces[i], x: faceX, y: faceY, w: faceSize, h: faceSize });
    }

    // 互动率大字
    s4.addText(`${v.rate}%`, {
      x: 6.5, y: y + 0.08, w: 1.0, h: 0.5,
      fontSize: 26, fontFace: "Arial Black", color: C.pink,
      align: "center", valign: "middle"
    });

    // 标题
    s4.addText(v.title, {
      x: 7.5, y: y + 0.1, w: 2.0, h: 0.35,
      fontSize: 10, fontFace: "Calibri", color: C.textDark, bold: true, valign: "middle"
    });
    // UP + 分区
    s4.addText(`${v.up} · ${v.region}`, {
      x: 7.5, y: y + 0.43, w: 2.0, h: 0.25,
      fontSize: 8, fontFace: "Calibri", color: C.textMid, valign: "middle"
    });
    // 播放量
    s4.addText(`播放 ${fmtNum(v.view)}`, {
      x: 7.5, y: y + 0.66, w: 2.0, h: 0.22,
      fontSize: 8, fontFace: "Calibri", color: C.textLight, valign: "middle"
    });
  });

  // ============================
  // SLIDE 5: 数据总览 (不变)
  // ============================
  const s5 = pres.addSlide();
  s5.background = { color: C.bg };

  s5.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.gold }
  });
  s5.addShape(pres.shapes.OVAL, {
    x: 7.5, y: 3.5, w: 3.5, h: 3.5,
    fill: { color: C.coral, transparency: 88 }
  });

  s5.addImage({ data: icons.star, x: 0.4, y: 0.35, w: 0.5, h: 0.5 });
  s5.addText("今日数据总览", {
    x: 1.0, y: 0.3, w: 6, h: 0.6,
    fontSize: 28, fontFace: "Arial Black", color: C.white, valign: "middle"
  });

  const totalPlay = top10.reduce((s, v) => s + v.view, 0);
  const totalLike = top10.reduce((s, v) => s + v.like, 0);

  const stats = [
    { label: "采样视频数", value: DATA.total_merged, color: C.coral, icon: icons.tv },
    { label: "覆盖分区数", value: regions.length + "+", color: C.gold, icon: icons.chart },
    { label: "TOP10 累计播放", value: fmtNum(totalPlay), color: C.teal, icon: icons.play },
    { label: "TOP10 累计点赞", value: fmtNum(totalLike), color: C.pink, icon: icons.heart },
  ];

  stats.forEach((s, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.5 + col * 4.6;
    const y = 1.3 + row * 1.5;

    s5.addShape(pres.shapes.RECTANGLE, {
      x: x, y: y, w: 4.2, h: 1.25,
      fill: { color: "2D3B52" },
      shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.2 }
    });
    s5.addShape(pres.shapes.RECTANGLE, {
      x: x, y: y, w: 0.08, h: 1.25, fill: { color: s.color }
    });
    s5.addImage({ data: s.icon, x: x + 0.25, y: y + 0.35, w: 0.5, h: 0.5 });
    s5.addText(s.value, {
      x: x + 0.9, y: y + 0.15, w: 3.1, h: 0.65,
      fontSize: 32, fontFace: "Arial Black", color: s.color,
      valign: "middle", bold: true
    });
    s5.addText(s.label, {
      x: x + 0.9, y: y + 0.78, w: 3.1, h: 0.35,
      fontSize: 12, fontFace: "Calibri", color: C.textLight, valign: "middle"
    });
  });

  s5.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.4, w: 9, h: 0.04, fill: { color: C.coral, transparency: 50 }
  });

  const topRegion = regions[0];
  const topPlayRegion = regionsPlay[0];
  s5.addText("今日洞察", {
    x: 0.5, y: 4.55, w: 3, h: 0.4,
    fontSize: 16, fontFace: "Arial Black", color: C.gold
  });

  const insights = [
    `上榜视频最多的分区: ${topRegion.name} (${topRegion.count}部)`,
    `累计播放最高的分区: ${topPlayRegion.name} (${fmtNum(topPlayRegion.play)})`,
    `综合热度冠军: ${top5[0].title.slice(0,25)} (热度 ${fmtNum(top5[0].heat)})`,
    `最高互动率: ${top3inter[0].title.slice(0,20)} (${top3inter[0].rate}%)`,
  ];

  insights.forEach((txt, i) => {
    s5.addText([
      { text: "▸ ", options: { color: C.coral, bold: true, fontSize: 12 } },
      { text: txt, options: { color: C.textLight, fontSize: 12 } },
    ], {
      x: 0.5, y: 5.0 + i * 0.22, w: 9, h: 0.22,
      fontFace: "Calibri", valign: "middle"
    });
  });

  // ===== 保存 =====
  const outPath = `/home/ubuntu/bilibili-daily/B站日报_${today}.pptx`;
  await pres.writeFile({ fileName: outPath });
  console.log(`PPT已生成: ${outPath}`);
}

main().catch(e => { console.error(e); process.exit(1); });

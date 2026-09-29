#let get_text(c) = {
  if type(c) == type("") { c }
  else if type(c) == content {
    if c.has("text") { c.text }
    else if c.has("children") {
      c.children.map(get_text).join("")
    }
    else if c.has("body") {
      get_text(c.body)
    }
    else { "" }
  } else { "" }
}

#let old_figure = figure
#let figure(..args) = {
  let cap = args.named().at("caption", default: none)
  let f = old_figure(..args)
  if cap != none {
    let cap_text = get_text(cap)
    if cap_text != "" and cap_text != none {
      let l = label(cap_text)
      [#f #l]
    } else { f }
  } else { f }
}

#let nested-block(indent-size: 2em, body) = {
  block(
    inset: (left: indent-size),
    [
      #text(size: 0pt)[]
      #h(1em)#body
    ]
  )
}

// ▼ 変更点：戻り値を figure 要素でラップし、参照可能な実体にしました
#let bib_term(id, author, title, source, publisher: none, publish_date, access_date: none) = {
  let label_id = "bib_" + id
  let is_url = type(source) == str and source.starts-with("http")

  assert(
    not (is_url and access_date == none),
    message: "エラー：URLの引用には access_date (閲覧日) が必須です！ ID: " + id,
  )

  let source_text = if is_url { link(source) } else { source }

  // 出力されるコンテンツ本体
  let content = [#author,#title,#source_text#if publisher != none [,#publisher],#publish_date#if access_date != none [,(参照：#access_date)]]
  
  // figureにしてkindを"bib"に設定。supplement(図などの接頭辞)は消す。直後にラベルを置く。
  [
    #let label_id = "bib_" + id
    #figure(content, kind: "bib", supplement: none, caption: none)#label(label_id)]
}

// ▼ 変更点：figure側でナンバリングするため enum の処理は不要になりました
#let bib-block(body, indent-size: 1em) = block(inset: (left: indent-size))[
  #body
]

#let Vin = $V_("in")$
#let Vrms = $V_("rms")$
#let Vout = $V_("out")$
#let ampere = $"A"$
#let waver = $"Wb"$
#let tesla = $"T"$
#let senti_meter = $"cm"$







#let dhpat(sep, stroke) = tiling(
  size: (10pt, (sep + std.stroke(stroke).thickness) * 10),
  {
    let t = std.stroke(stroke).thickness / 2 + 0.1pt
    let theline = line(length: 10pt, stroke: stroke)
    place(dy: t, theline)
    place(dy: t + sep, theline)
  },
)

#let dhhat(sep, stroke) = tiling(
  size: (10pt, (sep + std.stroke(stroke).thickness) * 10),
  {
    let t = std.stroke(stroke).thickness / 2 - 0.1pt
    let theline = line(length: 10pt, stroke: stroke)
    place(dy: t, theline)
    place(dy: t + sep, theline)
  },
)

#let mytable(header, cells, cols: none) = {
  // ▼ header の下に入れる太線
  let thickline = table.hline(
    stroke: (thickness: 6pt, paint: dhpat(2pt, 0.8pt))
  )

  if cols == none {
    table(
      columns: header.len(),
      table.hline(),                         // ← 一番上の細線
      table.header(..header.flatten()),
      thickline,                              // ← header の下の太線
      ..cells,
      table.hline(),                          // ← 最後の細線
    )
  } else {
    table(
      ..pillar.cols(cols),
      columns: header.len(),
      table.hline(),                         // ← 一番上の細線
      table.header(..header.flatten()),
      thickline,                              // ← header の下の太線
      ..cells,
      table.hline(),                          // ← 最後の細線
    )
  }
}



#let array_table(array, head) = {
  let header
  let data
  if head == none {
    header = array.at(0)
    data = array.slice(1)
  } else {
    header = head
    data = array
  }
  table(
    stroke: none,
    align: center,
    columns: header.len(),
    table.hline(stroke: (thickness: 6pt, paint: dhpat(2pt, 0.8pt), cap: "butt")),
    ..header,
    table.hline(),
    ..data.flatten(), table.hline(stroke: (thickness: 6pt, paint: dhhat(2pt, 0.8pt), cap: "butt")),
  )
}
#let csv2table(csv_path: "", header: none) = array_table(csv(csv_path), header)

#let meter = $"m"$
#let meterSq = $"m"^2$
#let gram = $"g"$
#let kiroGram = $"kg"$
#let uF = $upright(mu)"F"$


#let body(content) = [
  #set text(font: ("MS Mincho", "Yu Mincho"), size: 10.3pt, lang: "ja")
  #set par(first-line-indent: 1em)
  #set page(number-align: center, numbering: "1")
  #set heading(numbering: "1.1")
  #show heading: it => {
    [
      #set text(font: "HackGen Console NF", size: 12pt)
      #set par(first-line-indent: 0em) // 見出し自体には字下げを適用しない
      #if it.depth == 1 [
        \[#it.body\]#linebreak()
      ] else if it.depth == 2 [
        #let n = counter(heading).get().last()
        #h(it.depth * 0.25em)\(#n)#it.body
      ] else [
        #it.body
      ]]
  }
  #show old_figure.where(kind: image): set old_figure(supplement: "図")
  #show old_figure.where(kind: table): set old_figure(supplement: "表")
  #show old_figure.where(kind: table): set old_figure.caption(position: top)

  // ▼ 変更点：文献リストのレイアウトを整える（中央揃えを解除し番号を振る）
  #show old_figure.where(kind: "bib"): set old_figure(numbering: "[1]")
  #show old_figure.where(kind: "bib"): it => {
    set align(left)
    set block(breakable: true, spacing: 1em) // ページまたぎ許可、行間設定
    context {
      let num = counter(old_figure.where(kind: "bib")).at(it.location()).first()
      grid(
        columns: (auto, 1fr),
        column-gutter: 0.5em,
        [\[#num\]], it.body,
      )
    }
  }

  #show old_figure.caption: set text(font: "HackGen Console NF", size: 9pt)
  #set math.equation(supplement: "式", numbering: "(1)")
  #show math.equation: it => {
    if it.block {
      v(1em)
      it
    } else {
      [ #it ]
    }
  }

  // ▼ 変更点：参照の仕様を上書き
  #show ref: r => {
    let el = r.element
    if el != none and el.func() == math.equation {
      // 数式参照で「式(1)」とするため（デフォルトは括弧が外れてしまう仕様の回避）
      link(el.location(), [式#numbering(el.numbering, ..counter(math.equation).at(el.location()))])
    } else if el != none and el.func() == old_figure and el.kind == "bib" {
      // 独自のbib機能（figureの流用）の参照を上付きの[1]にするため
      link(el.location(), text(size: 0.5em, baseline: -0.75em, strong[#numbering(el.numbering, ..counter(old_figure.where(kind: "bib")).at(el.location()))]))
    } else {
      r
    }
  }

  #set image(width: 90%)
  #content
]

#let tempImage = text(
  red,
  size: 100pt,
)[
  仮！！！\
]

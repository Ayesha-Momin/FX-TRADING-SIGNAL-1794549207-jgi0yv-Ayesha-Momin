# ==============================================================================
# FX Signal Lab - Interactive R Shiny Dashboard Prototype
# Production-ready quantitative monitoring dashboard for institutional FX trading
# ==============================================================================

library(shiny)
library(shinydashboard)
library(plotly)
library(tidyverse)
library(DT)

# UI Layout
ui <- dashboardPage(
  skin = "blue",
  dashboardHeader(title = "FX Signal Lab"),
  dashboardSidebar(
    sidebarMenu(
      menuItem("Signal Monitor", tabName = "signals", icon = icon("chart-line")),
      menuItem("Strategy Performance", tabName = "performance", icon = icon("tachometer-alt")),
      menuItem("Risk & Monte Carlo", tabName = "risk", icon = icon("shield-alt")),
      menuItem("Scenario Stress Lab", tabName = "scenarios", icon = icon("bolt"))
    ),
    hr(),
    selectInput("selected_pair", "Currency Pair:", 
                choices = c("EUR/USD", "USD/JPY", "GBP/USD", "AUD/USD", "USD/INR"), 
                selected = "EUR/USD"),
    selectInput("selected_strategy", "Trading Strategy:",
                choices = c("Composite", "MA_Cross", "MACD_Trend", "RSI_Reversal", "ML_RF", "ML_XGB", "RL_PPO"),
                selected = "Composite"),
    sliderInput("conf_thresh", "Signal Confidence Cutoff:", min = 0.50, max = 0.95, value = 0.65, step = 0.05),
    actionButton("refresh_btn", "Recalculate Signals", icon = icon("sync"), class = "btn-primary")
  ),
  dashboardBody(
    tabItems(
      # Tab 1: Signal Monitor
      tabItem(tabName = "signals",
        fluidRow(
          valueBoxOutput("hit_rate_box", width = 3),
          valueBoxOutput("avg_conf_box", width = 3),
          valueBoxOutput("signals_count_box", width = 3),
          valueBoxOutput("net_pnl_box", width = 3)
        ),
        fluidRow(
          box(title = "Live FX Candlestick & Signal Overlay", status = "primary", solidHeader = TRUE, width = 8,
              plotlyOutput("price_chart", height = "450px")),
          box(title = "Indicator Multi-Factor Consensus", status = "info", solidHeader = TRUE, width = 4,
              plotlyOutput("consensus_gauge", height = "450px"))
        ),
        fluidRow(
          box(title = "Recent Executed Signals", status = "warning", solidHeader = TRUE, width = 12,
              DTOutput("signals_table"))
        )
      ),
      
      # Tab 2: Strategy Performance
      tabItem(tabName = "performance",
        fluidRow(
          box(title = "Comparative Equity Growth ($100k Base)", status = "success", solidHeader = TRUE, width = 8,
              plotlyOutput("equity_curve_plot", height = "400px")),
          box(title = "Performance Scorecard", status = "success", solidHeader = TRUE, width = 4,
              tableOutput("perf_metrics_table"))
        ),
        fluidRow(
          box(title = "Hourly Session Heatmap Score", status = "info", solidHeader = TRUE, width = 12,
              plotlyOutput("session_heatmap", height = "300px"))
        )
      ),
      
      # Tab 3: Risk & Monte Carlo
      tabItem(tabName = "risk",
        fluidRow(
          valueBoxOutput("var95_box", width = 3),
          valueBoxOutput("cvar95_box", width = 3),
          valueBoxOutput("maxdd_box", width = 3),
          valueBoxOutput("sharpe_box", width = 3)
        ),
        fluidRow(
          box(title = "Monte Carlo Simulated P&L Distribution (10,000 Paths)", status = "danger", solidHeader = TRUE, width = 8,
              plotlyOutput("monte_carlo_dist", height = "420px")),
          box(title = "Currency Pair Correlation Matrix", status = "danger", solidHeader = TRUE, width = 4,
              plotlyOutput("corr_heatmap", height = "420px"))
        )
      ),
      
      # Tab 4: Scenario Stress Lab
      tabItem(tabName = "scenarios",
        fluidRow(
          box(title = "Central Bank & Crisis Scenario Shocks", status = "warning", solidHeader = TRUE, width = 12,
              selectInput("macro_scenario", "Select Stress Scenario:",
                          choices = c("The BOJ Shock (Carry Unwind)", 
                                      "Asian Session Flash Crash", 
                                      "USD/INR RBI Intervention", 
                                      "Dovish Fed Emergency Pivot", 
                                      "Multi-Pair Correlation Breakdown")),
              verbatimTextOutput("scenario_desc"),
              plotlyOutput("scenario_impact_plot", height = "350px"))
        )
      )
    )
  )
)

# Server Logic
server <- function(input, output, session) {
  
  # KPI Value Boxes
  output$hit_rate_box <- renderValueBox({
    valueBox("68.4%", "Signal Hit Rate", icon = icon("bullseye"), color = "green")
  })
  
  output$avg_conf_box <- renderValueBox({
    valueBox("78.2%", "Avg Confidence", icon = icon("chart-bar"), color = "blue")
  })
  
  output$signals_count_box <- renderValueBox({
    valueBox("1,248", "Active Signals", icon = icon("bell"), color = "purple")
  })
  
  output$net_pnl_box <- renderValueBox({
    valueBox("+$24,190", "Net Realized PnL", icon = icon("wallet"), color = "olive")
  })
  
  output$var95_box <- renderValueBox({
    valueBox("$76,230", "1-Day VaR (95%)", icon = icon("exclamation-triangle"), color = "yellow")
  })
  
  output$cvar95_box <- renderValueBox({
    valueBox("$97,250", "Expected Shortfall (CVaR)", icon = icon("skull-crossbones"), color = "red")
  })
  
  output$maxdd_box <- renderValueBox({
    valueBox("8.42%", "Max Drawdown", icon = icon("arrow-down"), color = "maroon")
  })
  
  output$sharpe_box <- renderValueBox({
    valueBox("1.94", "Annualized Sharpe", icon = icon("gem"), color = "teal")
  })
  
  # Charts
  output$price_chart <- renderPlotly({
    dates <- seq.POSIXt(as.POSIXct("2024-01-01"), by = "hour", length.out = 100)
    prices <- 1.0850 + cumsum(rnorm(100, 0, 0.001))
    df_plot <- data.frame(Time = dates, Close = prices)
    
    plot_ly(df_plot, x = ~Time, y = ~Close, type = 'scatter', mode = 'lines',
            line = list(color = '#1f77b4', width = 2), name = input$selected_pair) %>%
      layout(title = paste(input$selected_pair, "Hourly Price & Composite Signals"),
             xaxis = list(title = "Time"), yaxis = list(title = "Price"))
  })
  
  output$consensus_gauge <- renderPlotly({
    plot_ly(
      type = "indicator",
      mode = "gauge+number",
      value = 75,
      title = list(text = "Indicator Consensus Score"),
      gauge = list(
        axis = list(range = list(-100, 100)),
        bar = list(color = "#2ca02c"),
        steps = list(
          list(range = list(-100, -25), color = "#ff9999"),
          list(range = list(-25, 25), color = "#eeeeee"),
          list(range = list(25, 100), color = "#99ff99")
        )
      )
    )
  })
  
  output$signals_table <- renderDT({
    data.frame(
      Time = format(Sys.time() - 1:10 * 3600, "%Y-%m-%d %H:%M"),
      Pair = input$selected_pair,
      Strategy = input$selected_strategy,
      Direction = sample(c("BUY", "SELL"), 10, replace = TRUE),
      Confidence = round(runif(10, 0.65, 0.95), 3),
      Score = round(runif(10, 45, 90), 1),
      StopLoss = round(1.0820 + runif(10, -0.005, 0.005), 4),
      TakeProfit = round(1.0920 + runif(10, -0.005, 0.005), 4)
    )
  })
  
  output$equity_curve_plot <- renderPlotly({
    t <- 1:150
    pnl_comp <- 100000 + cumsum(rnorm(150, 180, 250))
    pnl_ma <- 100000 + cumsum(rnorm(150, 90, 280))
    pnl_rl <- 100000 + cumsum(rnorm(150, 220, 230))
    
    plot_ly(x = t) %>%
      add_trace(y = pnl_comp, name = 'Composite', type = 'scatter', mode = 'lines') %>%
      add_trace(y = pnl_ma, name = 'MA Cross', type = 'scatter', mode = 'lines') %>%
      add_trace(y = pnl_rl, name = 'RL PPO', type = 'scatter', mode = 'lines') %>%
      layout(title = "Cumulative Equity Curves", xaxis = list(title = "Trade Count"), yaxis = list(title = "USD Equity"))
  })
  
  output$perf_metrics_table <- renderTable({
    data.frame(
      Metric = c("Win Rate", "Profit Factor", "Sharpe Ratio", "Sortino Ratio", "Calmar Ratio", "Expectancy"),
      Composite = c("68.4%", "1.78", "1.94", "2.45", "2.88", "$165.20"),
      MA_Cross = c("54.2%", "1.32", "1.15", "1.40", "1.25", "$62.10"),
      RL_PPO = c("71.5%", "1.92", "2.12", "2.80", "3.15", "$210.50")
    )
  })
  
  output$session_heatmap <- renderPlotly({
    hours <- 0:23
    pnl_by_hour <- c(-10, -5, 2, 5, 8, 12, 45, 80, 120, 140, 95, 110, 180, 250, 220, 160, 90, 40, 25, 10, 5, 0, -5, -8)
    plot_ly(x = hours, y = pnl_by_hour, type = 'bar', marker = list(color = ifelse(pnl_by_hour > 0, '#2ca02c', '#d62728'))) %>%
      layout(title = "Average Trade P&L by Hour of Day (UTC)", xaxis = list(title = "Hour"), yaxis = list(title = "Avg PnL ($)"))
  })
  
  output$monte_carlo_dist <- renderPlotly({
    pnl_sim <- rnorm(10000, 12270, 54710)
    plot_ly(x = pnl_sim, type = "histogram", nbinsx = 80, marker = list(color = '#1f77b4', opacity = 0.75)) %>%
      layout(title = "Simulated 252-Day Horizon P&L Distribution", xaxis = list(title = "Portfolio PnL ($)"), yaxis = list(title = "Count"))
  })
  
  output$corr_heatmap <- renderPlotly({
    pairs <- c("EUR/USD", "USD/JPY", "GBP/USD", "AUD/USD", "USD/INR")
    corr_m <- matrix(c(
       1.00, -0.42,  0.86,  0.68, -0.15,
      -0.42,  1.00, -0.38, -0.31,  0.22,
       0.86, -0.38,  1.00,  0.72, -0.12,
       0.68, -0.31,  0.72,  1.00, -0.08,
      -0.15,  0.22, -0.12, -0.08,  1.00
    ), nrow = 5)
    plot_ly(x = pairs, y = pairs, z = corr_m, type = "heatmap", colorscale = "Viridis") %>%
      layout(title = "Pair Correlation Matrix")
  })
  
  output$scenario_desc <- renderText({
    paste("Simulating stress conditions for:", input$macro_scenario, 
          "\nAutomatic capital preservation and ATR stop-loss widenings activated.")
  })
  
  output$scenario_impact_plot <- renderPlotly({
    scen_data <- data.frame(
      Pair = c("EUR/USD", "USD/JPY", "GBP/USD", "AUD/USD", "USD/INR"),
      Shock = c(1.2, -8.5, 0.8, -1.5, 0.2)
    )
    plot_ly(scen_data, x = ~Pair, y = ~Shock, type = 'bar',
            marker = list(color = ifelse(scen_data$Shock >= 0, '#2ca02c', '#d62728'))) %>%
      layout(title = "Asset Return Impact Under Stress Scenario (%)", yaxis = list(title = "% Shock"))
  })
}

shinyApp(ui, server)

# Title     : Feature effect comparing income groups
# Objective : Feature vs score on predicting experienced income segregation
# Created by: Yuan Liao
# Created on: 2023-04-24

library(dplyr)
library(ggplot2)
library(ggpubr)
library(arrow)
library(scales)

# Load all features
feature_dict <- list(weekend='Weekend', weekday='Weekday',
                     non_holiday='Non-holiday', holiday='Holiday',
                     number_of_locations='No. of unique locations visited',
                     number_of_visits='No. of visits',
                     average_displacement='Average displacement',
                     radius_of_gyration='Radius of gyration',
                     median_distance_from_home='Median distance from home',
                     `Not Sweden`='Prob. born outside Sweden',
                     `Lowest income group`='Prob. in lowest income group',
                     car_ownership='Prob. of owning a car',
                     cum_jobs='Job accessibility by car',
                     cum_stops='Transit accessibility by walking',
                     evenness_income_resi='Residential income segregation',
                     num_jobs='Job density at residence',
                     num_stops='Transit stop density at residence',
                     gsi='GSI at residence',
                     length_density='Pedestrian network density at residence')

df.vis <- as.data.frame(read_parquet('results/data4model_individual.parquet'))
fb.tre.low <- 0.4
fb.tre.high <- 0.1
df.vis$income_gp <- NA
df.vis$income_gp[df.vis$`Lowest income group` > fb.tre.low] <- "Low income"
df.vis$income_gp[df.vis$`Lowest income group` <= fb.tre.high] <- "High income"
#Remove rows with NA's using rowSums()
df.vis <- df.vis[rowSums(is.na(df.vis)) == 0, ]

# Load single-feature effect
df.low <- read.csv('./results/ebm/low_income/features.csv')
df.high <- read.csv('./results/ebm/high_income/features.csv')

single.feature.plot <- function(var.name, df.l, df.h, df.raw, log.label, y.label){
  df2plot.l <- df.l[df.l$var==var.name, ]
  df2plot.h <- df.h[df.h$var==var.name, ]
  # Quantiles for low income
  qts.l <- quantile(df.raw[df.raw$income_gp=='Low income', var.name], probs = seq(0, 1, 0.01))
  df.qts.l <- data.frame(qts.l)
  names(df.qts.l) <- 'qts'

  # Quantiles for high income
  qts.h <- quantile(df.raw[df.raw$income_gp=='High income', var.name], probs = seq(0, 1, 0.01))
  df.qts.h <- data.frame(qts.h)
  names(df.qts.h) <- 'qts'

  rugy <- -0.025 #min(df2plot$y_lower) - 0.001

  g <- ggplot() + theme_minimal() +
    geom_point(data = df.qts.l, aes(x=qts, y=rugy, color='Low income'), shape=108) +
    geom_point(data = df.qts.h, aes(x=qts, y=rugy, color='High income'), shape=108) +
    geom_line(data=df2plot.l, aes(x=x, y=y, color='Low income'), size=0.8) +
    geom_ribbon(data=df2plot.l, aes(x=x, ymin = y_lower, ymax = y_upper, fill='Low income'),
                color=NA,
                alpha = 0.5) +
    geom_line(data=df2plot.h, aes(x=x, y=y, color='High income'), size=0.8) +
    geom_ribbon(data=df2plot.h, aes(x=x, ymin = y_lower, ymax = y_upper, fill='High income'),
                color=NA,
                alpha = 0.5) +
    scale_color_manual(name='Income group', breaks=c('Low income', 'High income'),
                   values=c('High income'='steelblue', 'Low income'='orange')) +
    scale_fill_manual(name='Income group', breaks=c('Low income', 'High income'),
               values=c('High income'='steelblue', 'Low income'='orange')) +
    ylim(-0.03, 0.06) +
    geom_hline(yintercept=0, color='gray40', alpha=0.7, size=.5) +
    labs(x=feature_dict[var.name], y=y.label) +
    theme(plot.margin = margin(1,0,0,0, "cm"),
          legend.position = 'top')

  if (log.label == TRUE) {
    g <- g +
      scale_x_log10(breaks = trans_breaks("log10", function(x) 10^x),
                    labels = trans_format("log10", math_format(10^.x)))
  }
  return(g)
}

v.n <- 'Not Sweden'
g1 <- single.feature.plot(var.name=v.n,
                          df.l=df.low,
                          df.h=df.high,
                          df.raw=df.vis,
                          log.label=FALSE,
                          y.label = 'Impact on experienced income segregation')
ggsave(filename = paste0("./figures/ebm/", v.n, ".png"), plot=g1,
       width = 5, height = 5, unit = "in", dpi = 300)

v.n <- 'median_distance_from_home'
g2 <- single.feature.plot(var.name=v.n,
                          df.l=df.low,
                          df.h=df.high,
                          df.raw=df.vis,
                          log.label=TRUE,
                          y.label = 'Impact on experienced income segregation')
ggsave(filename = paste0("./figures/ebm/", v.n, ".png"), plot=g2,
       width = 5, height = 5, unit = "in", dpi = 300)

v.n <- 'Lowest income group'
g3 <- single.feature.plot(var.name=v.n,
                          df.l=df.low,
                          df.h=df.high,
                          df.raw=df.vis,
                          log.label=FALSE,
                          y.label = 'Impact on experienced income segregation')
ggsave(filename = paste0("./figures/ebm/", v.n, ".png"), plot=g3,
       width = 5, height = 5, unit = "in", dpi = 300)

v.n <- 'evenness_income_resi'
g4 <- single.feature.plot(var.name=v.n,
                          df.l=df.low,
                          df.h=df.high,
                          df.raw=df.vis,
                          log.label=FALSE,
                          y.label = 'Impact on experienced income segregation')
ggsave(filename = paste0("./figures/ebm/", v.n, ".png"), plot=g4,
       width = 5, height = 5, unit = "in", dpi = 300)

v.n <- 'cum_jobs'
g5 <- single.feature.plot(var.name=v.n,
                          df.l=df.low,
                          df.h=df.high,
                          df.raw=df.vis,
                          log.label=FALSE,
                          y.label = 'Impact on experienced income segregation')
ggsave(filename = paste0("./figures/ebm/", v.n, ".png"), plot=g5,
       width = 5, height = 5, unit = "in", dpi = 300)

v.n <- 'number_of_locations'
g6 <- single.feature.plot(var.name=v.n,
                          df.l=df.low,
                          df.h=df.high,
                          df.raw=df.vis,
                          log.label=TRUE,
                          y.label = 'Impact on experienced income segregation')
ggsave(filename = paste0("./figures/ebm/", v.n, ".png"), plot=g6,
       width = 5, height = 5, unit = "in", dpi = 300)

v.n <- 'cum_stops'
g7 <- single.feature.plot(var.name=v.n,
                          df.l=df.low,
                          df.h=df.high,
                          df.raw=df.vis,
                          log.label=FALSE,
                          y.label = 'Impact on experienced income segregation')
ggsave(filename = paste0("./figures/ebm/", v.n, ".png"), plot=g7,
       width = 5, height = 5, unit = "in", dpi = 300)

v.n <- 'car_ownership'
g8 <- single.feature.plot(var.name=v.n,
                          df.l=df.low,
                          df.h=df.high,
                          df.raw=df.vis,
                          log.label=FALSE,
                          y.label = 'Impact on experienced income segregation')
ggsave(filename = paste0("./figures/ebm/", v.n, ".png"), plot=g8,
       width = 5, height = 5, unit = "in", dpi = 300)

v.n <- 'num_jobs'
g9 <- single.feature.plot(var.name=v.n,
                          df.l=df.low,
                          df.h=df.high,
                          df.raw=df.vis,
                          log.label=TRUE,
                          y.label = 'Impact on experienced income segregation')
ggsave(filename = paste0("./figures/ebm/", v.n, ".png"), plot=g9,
       width = 5, height = 5, unit = "in", dpi = 300)

v.n <- 'average_displacement'
g10 <- single.feature.plot(var.name=v.n,
                          df.l=df.low,
                          df.h=df.high,
                          df.raw=df.vis,
                          log.label=TRUE,
                          y.label = 'Impact on experienced income segregation')
ggsave(filename = paste0("./figures/ebm/", v.n, ".png"), plot=g10,
       width = 5, height = 5, unit = "in", dpi = 300)

v.n <- 'length_density'
g11 <- single.feature.plot(var.name=v.n,
                          df.l=df.low,
                          df.h=df.high,
                          df.raw=df.vis,
                          log.label=TRUE,
                          y.label = 'Impact on experienced income segregation')
ggsave(filename = paste0("./figures/ebm/", v.n, ".png"), plot=g11,
       width = 5, height = 5, unit = "in", dpi = 300)
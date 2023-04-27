# Title     : Feature effect
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

# Load single-feature effect
df <- read.csv('./results/ebm/features.csv')

single.feature.plot <- function(var.name, df, df.raw, log.label, y.label){
  df2plot <- df[df$var==var.name, ]
  qts <- quantile(df.raw[,var.name], probs = seq(0, 1, 0.01))
  df.qts <- data.frame(qts)
  names(df.qts) <- 'qts'
  rugy <- -0.025 #min(df2plot$y_lower) - 0.001

  g <- ggplot(data = df2plot) + theme_minimal() +
    geom_point(data = df.qts, aes(x=qts, y=rugy), shape=108) +
    geom_line(aes(x=x, y=y), size=0.8) +
    geom_ribbon(aes(x=x, ymin = y_lower, ymax = y_upper),
                fill='royalblue4', color=NA,
                alpha = 0.5) +
    ylim(-0.03, 0.06) +
    geom_hline(yintercept=0, color='gray40', alpha=0.7, size=.5) +
    labs(x=feature_dict[var.name], y=y.label) +
    theme(plot.margin = margin(1,0,0,0, "cm"))

  if (log.label == TRUE) {
    g <- g +
      scale_x_log10(breaks = trans_breaks("log10", function(x) 10^x),
                    labels = trans_format("log10", math_format(10^.x)))
  }
  return(g)
}

g1 <- single.feature.plot(var.name='number_of_locations', df=df, df.raw=df.vis, log.label=TRUE, y.label = 'Impact on experienced income segregation')
g2 <- single.feature.plot(var.name='evenness_income_resi', df=df, df.raw=df.vis, log.label=FALSE, y.label = ' ')
g3 <- single.feature.plot(var.name='Lowest income group', df=df, df.raw=df.vis, log.label=FALSE, y.label = ' ')
g4 <- single.feature.plot(var.name='cum_jobs', df=df, df.raw=df.vis, log.label=TRUE, y.label = ' ')
g5 <- single.feature.plot(var.name='num_jobs', df=df, df.raw=df.vis, log.label=TRUE, y.label = ' ')
g6 <- single.feature.plot(var.name='Not Sweden', df=df, df.raw=df.vis, log.label=FALSE, y.label = 'Impact on experienced income segregation')
g7 <- single.feature.plot(var.name='average_displacement', df=df, df.raw=df.vis, log.label=TRUE, y.label = ' ')
g8 <- single.feature.plot(var.name='car_ownership', df=df, df.raw=df.vis, log.label=FALSE, y.label = ' ')
g9 <- single.feature.plot(var.name='gsi', df=df, df.raw=df.vis, log.label=FALSE, y.label = ' ')
g10 <- single.feature.plot(var.name='cum_stops', df=df, df.raw=df.vis, log.label=TRUE, y.label = ' ')

# Save figure
G <- ggarrange(g1, g2, g3, g4, g5,
               g6, g7, g8, g9, g10,
               labels = c('(a)', '(b)', '(c)', '(d)', '(e)',
                          '(f)', '(g)', '(h)', '(i)', '(j)'),
               ncol = 5, nrow = 2)
ggsave(filename = "./figures/feature_curve.png", plot=G,
       width = 15, height = 7, unit = "in", dpi = 300)

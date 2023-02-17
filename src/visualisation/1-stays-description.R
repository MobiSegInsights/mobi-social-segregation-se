# Title     : Data description
# Objective : Visualise the distributions of key statistics
# Created by: Yuan Liao
# Created on: 2023-02-13


library(dplyr)
library(pastecs)
library(ggplot2)
library(DBI)
library(RPostgres)
library(yaml)
library(ggsci)
library(ggpubr)
library(data.table)
library(scales) # to access break formatting functions

# Load descriptive stats from the database
keys_manager <- read_yaml('./dbs/keys.yaml')
user <- keys_manager$database$user
password <- keys_manager$database$password
port <- keys_manager$database$port
db_name <- keys_manager$database$name
con <- DBI::dbConnect(RPostgres::Postgres(),
                      host = "localhost",
                      dbname = db_name,
                      user = user,
                      password = password,
                      port = port)
df <- dbGetQuery(con, 'SELECT * FROM description.stops')
selected <- dbGetQuery(con, 'SELECT * FROM home_sub')
df <- df %>%
  filter(df$uid %in% selected$uid)

vars <- c("# of days", "# of active stays", "# of stays per active day",
          "Total duration per active day, hours", "Duration per stay, min")
var.names <- names(df)
var.names <- var.names[! var.names == 'uid']
names(vars) <- var.names

plot.var.ccdf <- function(df, var, vars){
  # get the ecdf - Empirical Cumulative Distribution Function of v
  my_ecdf <- ecdf( df[,var] )
  # now put the ecdf and its complementary in a data.frame
  df2plot <- data.frame( x = sort(df[,var]), y = 1-my_ecdf(sort(df[,var])) )

  g <- ggplot(data=df2plot) +
    theme_minimal() +
    geom_point(aes(x=x, y=y), color = 'steelblue', size=0.1) +
    labs(x=paste(vars[[var]], "(x)"), y="P(X > x)") +
    scale_x_log10(breaks = trans_breaks("log10", function(x) 10^x),
                  labels = trans_format("log10", math_format(10^.x))) +
    scale_y_log10(breaks = trans_breaks("log10", function(x) 10^x),
                  labels = trans_format("log10", math_format(10^.x))) +
    annotation_logticks() +
    theme(plot.margin = margin(1,0,0,0, "cm"))
  return(g)
}
# Visualise the distributions
glist1 <- lapply(var.names[1:4], function(x){plot.var.ccdf(df, x, vars)})
g2 <- plot.var.ccdf(df, var.names[5], vars)
# Add a summary table
# Draw the summary table of variables
#::::::::::::::::::::::::::::::::::::::
# Compute descriptive statistics by groups
df$dur_total_act <- round(df$dur_total_act, digits=1)
df$dur_median <- round(df$dur_median, digits=1)
stable <- stat.desc(df)
stable <- transpose(stable["median", var.names])
names(stable) <- c('Median')
# Summary table plot, medium orange theme
stable.p <- ggtexttable(stable, rows = vars,
                        theme = ttheme("light"))
G1 <- ggarrange(plotlist=glist1, nrow = 2, ncol = 2, labels = c('(a)', '(b)', '(d)', '(e)'))
G2 <- ggarrange(g2, stable.p, nrow = 2, ncol = 1, labels = c('(c)', '(f)'))
G <- ggarrange(G1, G2, nrow = 1, ncol = 2, widths = c(1.5, 1))

ggsave(filename = "figures/data_description.png", plot=G,
     width = 9, height = 6, unit = "in", dpi = 300)
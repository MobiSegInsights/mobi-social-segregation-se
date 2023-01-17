#
# This is the server logic of a Shiny web application. You can run the
# application by clicking 'Run App' above.
#
# Find out more about building applications with Shiny here:
#
#    http://shiny.rstudio.com/
#

library(shiny)
options(scipen = 0)
# Define server logic required to draw a histogram
function(input, output, session) {

    zones <- st_transform(st_read('data/resi_segregation.shp'), crs = 4326)
    
    layer <- reactive({
        # Subsetting data based on input$mode and input$hour from ui.R
        asp_names <- list(background='b', income='inc', birth_region='rb')
        tp_names <- list(evenness='S_', isolation='iso_')
        asp <- input$aspect
        tp <- input$type
        col2plot <- paste0(tp_names[tp], asp_names[asp])
        return(col2plot)
    })
    
    output$selected_aspect <- renderText({ 
        if (input$aspect == 'income'){out <- "Net income: the sum of all taxable and tax-free income of a person minus tax and 
            other negative transfers (eg., repaid student loan). There are four quantile groups. Exposure measures the lowest income group."}
        if (input$aspect == 'background') {out <- "Foreign background has two groups: 1) persons with a foreign background are defined as persons who were born abroad, or born in Denmark with two foreign-born parents.
               2) Persons with a Swedish background are defined as persons who were born in Sweden to two Swedish-born parents or one Swedish-born and one foreign-born parent.
            Exposure measures the foreign background."}
        if (input$aspect == 'birth_region') {out <- "Region of birth has three groups: 1) Sweden, 2) Europe except Sweden, and 3) the rest of world incl. unknown. Europe except Sweden = The Nordic countries, EU countries and the rest of
              Europe including Russia and Turkey. Exposure measures the groups that were born outside Sweden."}
        out
    })
    
    output$selected_type <- renderText({ 
        if (input$type == 'evenness'){out <- "Evenness: a higher value indicates a bigger difference between the social group sizes in a region."}
        if (input$type == 'isolation'){out <- "Exposure: a higher value indicates a certain social group being more isolated in a region. 
        This measures the extent to which a certain group of people are exposed only to one other, rather than to the others."}
        out
    })
    
    output$segPlot <- renderMapdeck({
        key <- "pk.eyJ1IjoieXVhbmxpYW8iLCJhIjoiY2xkMGl6bGw1MWRqODNycDdiMmdoMzR1eSJ9.cW2c9yeQZG27b8Z37EUeVg"
        mapdeck(token = key, location = c(11.974116, 57.690063)
                , zoom = 14
                , style = mapdeck_style("street")
            ) %>%
            add_polygon(
                data = zones
                , layer = "polygon_layer"
                , fill_colour = layer()
                , legend = TRUE
                , legend_options = list(digits = 5)
                , fill_opacity = 200
                , update_view = F
            )
        
    })

}

require 'launchy'

desc "Cleans and builds the presentation"
task default: %w[clean build]

desc "Cleans the \"built\", (removes the presentation/slides folder)"
task :clean do
    `rm -rf presentation/slides`
end

desc "Builds the presentation, which can be found in presentation/slides/presentation.html"
task :build do
    `bundle exec slideshow build presentation/presentation.md -o presentation/slides -t reveal`
    `cp presentation/presentation.css presentation/slides/`
    `cp -r presentation/images presentation/slides/`
end

desc "Opens the presentation in browser (presentation/slides/presentation.html)"
task :show do
  Launchy.open('presentation/slides/presentation.html')
end

desc "Creates an UGLY pdf version of the presentation (presentation/slides/presentation.pdf)"
task :pdf do
   `rm -rf presentation/slides/pdf`
  `bundle exec slideshow build presentation/presentation.md -o presentation/slides/pdf`
  `wkhtmltopdf --outline presentation/slides/pdf/presentation.pdf.html presentation/slides/presentation.pdf`
   `rm -rf presentation/slides/pdf`
end
